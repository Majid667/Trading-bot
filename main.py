import asyncio
import logging
import sys
from datetime import datetime, time
from trading_engine import TradingEngine
from dashboard import start_dashboard
from config import Config

# Configure logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(Config.LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)

logger = logging.getLogger(__name__)


class BotManager:
    def __init__(self):
        self.engine = TradingEngine()
        self.is_running = False
        self.session_start = datetime.now()

    def log_session_summary(self):
        """Log trading session summary."""
        stats = self.engine.get_daily_stats()
        duration = (datetime.now() - self.session_start).total_seconds() / 60

        logger.info("=" * 60)
        logger.info("TRADING SESSION SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Duration: {duration:.1f} minutes")
        logger.info(f"Total Trades: {stats['total_trades']}")
        logger.info(f"Winning Trades: {stats['winning_trades']}")
        logger.info(f"Losing Trades: {stats['losing_trades']}")
        logger.info(f"Win Rate: {stats['win_rate']:.2f}%")
        logger.info(f"Total P&L: ${stats['total_profit']:.2f}")
        logger.info(f"ROI: {stats['roi_percent']:.2f}%")
        logger.info(f"Final Balance: ${stats['current_balance']:.2f}")
        logger.info("=" * 60)

    async def scan_and_trade(self):
        """Main trading loop - scan markets and execute trades."""
        iteration = 0
        last_reset_date = datetime.now().date()

        while self.is_running:
            iteration += 1
            current_date = datetime.now().date()

            # Reset daily stats if it's a new day
            if current_date != last_reset_date:
                self.engine.reset_daily_stats()
                logger.info(f"Daily reset: New day ({current_date}). Ready to trade!")
                last_reset_date = current_date

            logger.info(f"--- Iteration {iteration} ---")

            # 1. Check if we should trade (based on time/conditions)
            if not self.should_trade():
                logger.debug("Trading conditions not met, waiting...")
                await asyncio.sleep(5)
                continue

            # 2. Check if trading was stopped for today
            if self.engine.trading_stopped_today:
                logger.warning(
                    f"Trading stopped for today - Lost 3 trades. "
                    f"Come back tomorrow! (Losing trades: {self.engine.daily_losing_trades}/3)"
                )
                await asyncio.sleep(30)  # Wait longer between checks
                continue

            # 3. Find trading opportunities
            opportunities = self.engine.find_trading_opportunities()
            if not opportunities:
                logger.info("No trading opportunities found")
                await asyncio.sleep(5)
                continue

            logger.info(f"Found {len(opportunities)} potential opportunities")

            # 4. Analyze and enter trades
            for market in opportunities:
                if self.engine.daily_trades_count >= Config.MAX_TRADES_PER_DAY:
                    logger.warning("Daily trade limit reached")
                    break

                signal = self.engine.calculate_entry_signal(market)
                if signal:
                    trade = self.engine.enter_trade(signal)
                    if trade:
                        logger.info(f"✓ Entered {trade.trade_id}")
                    else:
                        # Check if stopped due to losing trades
                        if self.engine.trading_stopped_today:
                            logger.warning(
                                f"Trading stopped - Reached 3 losing trades today"
                            )
                            break

            # 5. Monitor open trades
            trades_to_remove = []
            for trade_id, trade in self.engine.open_trades.items():
                # Get current market price
                market_price = self.engine.client.get_market_price(trade.market_id)
                if market_price:
                    current_price = market_price.get("price", trade.entry_price)
                    exit_signal = self.engine.update_trade(trade, current_price)
                    if exit_signal:
                        trades_to_remove.append(trade_id)
                        logger.info(
                            f"✓ {trade_id} closed - Profit/Loss: ${trade.profit_loss:.2f}"
                        )

            # 6. Update balance and log status
            stats = self.engine.get_daily_stats()
            logger.info(
                f"Balance: ${stats['current_balance']:.2f} | "
                f"Trades: {stats['total_trades']} | "
                f"Losing Trades: {stats['daily_losing_trades']}/{stats['max_losing_trades_allowed']} | "
                f"Win Rate: {stats['win_rate']:.1f}% | "
                f"P&L: ${stats['total_profit']:.2f}"
            )

            # Wait before next iteration (5 seconds between scans)
            await asyncio.sleep(5)

    def should_trade(self) -> bool:
        """Check if bot should be trading based on conditions."""
        if Config.TRADE_24_7:
            return True

        current_time = datetime.now().time()
        # Example: Only trade 9 AM - 4 PM
        trading_start = time(9, 0)
        trading_end = time(16, 0)
        return trading_start <= current_time <= trading_end

    def start(self, with_dashboard: bool = True):
        """Start the trading bot."""
        logger.info("Starting BTC 5-Minute Scalping Bot")
        logger.info(f"Starting Balance: ${Config.STARTING_BALANCE}")
        logger.info(f"Position Size: {Config.POSITION_SIZE_PERCENT}%")
        logger.info(f"Profit Target: {Config.PROFIT_TARGET_PERCENT}%")
        logger.info(f"Stop Loss: {Config.STOP_LOSS_PERCENT}%")
        logger.info(f"Max Losing Trades/Day: {Config.MAX_LOSING_TRADES_PER_DAY}")

        self.is_running = True

        if with_dashboard:
            # Start dashboard in a separate thread
            import threading

            dashboard_thread = threading.Thread(
                target=lambda: start_dashboard(self.engine), daemon=True
            )
            dashboard_thread.start()
            logger.info("Dashboard started on http://localhost:5000")

        # Run the trading loop
        try:
            asyncio.run(self.scan_and_trade())
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            self.stop()
        except Exception as e:
            logger.error(f"Bot error: {e}", exc_info=True)
            self.stop()

    def stop(self):
        """Stop the trading bot."""
        self.is_running = False
        self.log_session_summary()
        logger.info("Bot stopped")


def main():
    """Entry point."""
    manager = BotManager()
    manager.start(with_dashboard=True)


if __name__ == "__main__":
    main()