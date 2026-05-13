import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Polymarket API
    POLYMARKET_API_KEY = os.getenv("POLYMARKET_API_KEY", "")
    POLYMARKET_API_SECRET = os.getenv("POLYMARKET_API_SECRET", "")
    POLYMARKET_API_URL = "https://api.polymarket.com"

    # Trading Parameters
    STARTING_BALANCE = 100.0
    POSITION_SIZE_PERCENT = 5.0  # 5% of balance per trade
    PROFIT_TARGET_PERCENT = 1.0  # 1% profit target
    STOP_LOSS_PERCENT = 0.3  # 0.3% stop loss
    MAX_TRADES_PER_DAY = 100

    # Market Selection
    MARKET_TYPE = "BTC"  # BTC 5-minute markets
    MIN_VOLUME_THRESHOLD = 10000  # Only trade if volume above this
    TIMEFRAME = "5m"

    # Risk Management
    MAX_DAILY_LOSS_PERCENT = 5.0  # Stop trading if down 5% for the day
    MIN_SPREAD_PERCENT = 0.5  # Only trade if spread > 0.5%

    # Trading Hours
    TRADE_24_7 = True

    # Logging
    LOG_LEVEL = "INFO"
    LOG_FILE = "trading_bot.log"

    def get_position_size(self, balance):
        return (balance * self.POSITION_SIZE_PERCENT) / 100

    def get_profit_target(self, entry_price):
        return entry_price * (1 + self.PROFIT_TARGET_PERCENT / 100)

    def get_stop_loss(self, entry_price):
        return entry_price * (1 - self.STOP_LOSS_PERCENT / 100)