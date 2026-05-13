import logging
from datetime import datetime
from typing import Dict, Optional, List
from enum import Enum
from config import Config
from polymarket_client import PolymarketClient

logger = logging.getLogger(__name__)


class TradeState(Enum):
    SEARCHING = "searching"
    ENTRY_SIGNAL = "entry_signal"
    ENTERED = "entered"
    PROFIT_TARGET_HIT = "profit_target_hit"
    STOP_LOSS_HIT = "stop_loss_hit"
    CLOSED = "closed"


class Trade:
    def __init__(self, trade_id: str, market_id: str, entry_price: float, position_size: float):
        self.trade_id = trade_id
        self.market_id = market_id
        self.entry_price = entry_price
        self.position_size = position_size
        self.entry_time = datetime.now()
        self.exit_price: Optional[float] = None
        self.exit_time: Optional[datetime] = None
        self.state = TradeState.ENTERED
        self.profit_loss = 0.0

    def check_exit(self, current_price: float) -> Optional[str]:
        """Check if trade should exit (profit target or stop loss)."""
        profit_target = Config.get_profit_target(None, self.entry_price)
        stop_loss = Config.get_stop_loss(None, self.entry_price)

        if current_price >= profit_target:
            self.state = TradeState.PROFIT_TARGET_HIT
            return "PROFIT_TARGET"
        elif current_price <= stop_loss:
            self.state = TradeState.STOP_LOSS_HIT
            return "STOP_LOSS"
        return None

    def close(self, exit_price: float):
        """Close the trade and calculate P&L."""
        self.exit_price = exit_price
        self.exit_time = datetime.now()
        self.profit_loss = (exit_price - self.entry_price) * self.position_size
        self.state = TradeState.CLOSED

    def duration_seconds(self) -> int:
        """Get trade duration in seconds."""
        end_time = self.exit_time or datetime.now()
        return int((end_time - self.entry_time).total_seconds())

    def to_dict(self) -> Dict:
        return {
            "trade_id": self.trade_id,
            "market_id": self.market_id,
            "entry_price": self.entry_price,
            "exit_price": self.exit_price,
            "position_size": self.position_size,
            "entry_time": self.entry_time.isoformat(),
            "exit_time": self.exit_time.isoformat() if self.exit_time else None,
            "profit_loss": self.profit_loss,
            "duration_seconds": self.duration_seconds(),
            "state": self.state.value,
        }


class TradingEngine:
    def __init__(self):
        self.client = PolymarketClient()
        self.balance = Config.STARTING_BALANCE
        self.trades: List[Trade] = []
        self.open_trades: Dict[str, Trade] = {}
        self.daily_trades_count = 0
        self.daily_loss = 0.0
        self.trade_counter = 0

    def is_valid_market(self, market: Dict) -> bool:
        """Check if market meets trading criteria."""
        volume = market.get("volume_24h", 0)
        spread = market.get("spread_percent", 0)

        return (
            volume >= Config.MIN_VOLUME_THRESHOLD
            and spread >= Config.MIN_SPREAD_PERCENT
            and market.get("timeframe") == Config.TIMEFRAME
        )

    def find_trading_opportunities(self) -> List[Dict]:
        """Find BTC 5-min markets with good trading conditions."""
        markets = self.client.get_btc_markets()
        valid_markets = [m for m in markets if self.is_valid_market(m)]
        return valid_markets[:10]  # Return top 10 opportunities

    def calculate_entry_signal(self, market: Dict) -> Optional[Dict]:
        """Analyze market and generate entry signal if conditions are met."""
        volume = market.get("volume_24h", 0)
        bid = market.get("bid_price", 0)
        ask = market.get("ask_price", 0)
        spread = ask - bid

        if spread <= 0 or volume <= 0:
            return None

        spread_percent = (spread / bid) * 100 if bid > 0 else 0

        # Entry condition: High volume + tight spread + trending up
        if (
            volume >= Config.MIN_VOLUME_THRESHOLD
            and spread_percent >= Config.MIN_SPREAD_PERCENT
        ):
            return {
                "market_id": market.get("id"),
                "entry_price": ask,  # Buy at ask price
                "position_size": Config.get_position_size(None, self.balance),
                "confidence": min(100, (volume / Config.MIN_VOLUME_THRESHOLD) * 10),
            }
        return None

    def enter_trade(self, signal: Dict) -> Optional[Trade]:
        """Execute entry based on signal."""
        if self.daily_trades_count >= Config.MAX_TRADES_PER_DAY:
            logger.warning("Max trades per day reached")
            return None

        if self.daily_loss >= (self.balance * Config.MAX_DAILY_LOSS_PERCENT / 100):
            logger.warning("Daily loss limit exceeded, stopping trades")
            return None

        self.trade_counter += 1
        trade = Trade(
            trade_id=f"TRADE_{self.trade_counter}",
            market_id=signal["market_id"],
            entry_price=signal["entry_price"],
            position_size=signal["position_size"],
        )

        # Place order on Polymarket
        order = self.client.place_order(
            market_id=trade.market_id,
            side="BUY",
            amount=trade.position_size,
            price=trade.entry_price,
        )

        if order:
            self.open_trades[trade.trade_id] = trade
            self.daily_trades_count += 1
            logger.info(
                f"Entered trade {trade.trade_id} at ${trade.entry_price:.4f} "
                f"with size {trade.position_size:.2f}"
            )
            return trade
        else:
            logger.error(f"Failed to place order for {trade.trade_id}")
            return None

    def update_trade(self, trade: Trade, current_price: float) -> Optional[str]:
        """Monitor open trade and check exit conditions."""
        exit_signal = trade.check_exit(current_price)

        if exit_signal:
            self.exit_trade(trade, current_price)
            logger.info(
                f"Trade {trade.trade_id} closed via {exit_signal} at ${current_price:.4f}"
            )
            return exit_signal

        return None

    def exit_trade(self, trade: Trade, exit_price: float):
        """Close a trade at given price."""
        trade.close(exit_price)
        self.balance += trade.profit_loss
        self.daily_loss += trade.profit_loss if trade.profit_loss < 0 else 0

        # Cancel order on Polymarket if still open
        self.client.cancel_order(trade.market_id)

        # Move from open to closed trades
        if trade.trade_id in self.open_trades:
            del self.open_trades[trade.trade_id]
        self.trades.append(trade)

    def get_daily_stats(self) -> Dict:
        """Get trading statistics for the day."""
        closed_trades = [t for t in self.trades if t.state == TradeState.CLOSED]
        winning_trades = [t for t in closed_trades if t.profit_loss > 0]
        losing_trades = [t for t in closed_trades if t.profit_loss < 0]

        total_profit = sum(t.profit_loss for t in closed_trades)
        win_rate = len(winning_trades) / len(closed_trades) * 100 if closed_trades else 0

        return {
            "total_trades": len(closed_trades),
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "win_rate": win_rate,
            "total_profit": total_profit,
            "current_balance": self.balance,
            "roi_percent": (total_profit / Config.STARTING_BALANCE) * 100,
        }

    def reset_daily_stats(self):
        """Reset daily counters."""
        self.daily_trades_count = 0
        self.daily_loss = 0.0