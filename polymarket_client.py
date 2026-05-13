import requests
import logging
from config import Config
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class PolymarketClient:
    def __init__(self, api_key: str = None, api_secret: str = None):
        self.api_key = api_key or Config.POLYMARKET_API_KEY
        self.api_secret = api_secret or Config.POLYMARKET_API_SECRET
        self.base_url = Config.POLYMARKET_API_URL
        self.session = requests.Session()
        self.session.headers.update(self._get_headers())

    def _get_headers(self) -> Dict:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

    def get_btc_markets(self) -> List[Dict]:
        """Fetch all BTC 5-minute markets."""
        try:
            endpoint = f"{self.base_url}/markets"
            params = {
                "category": "crypto",
                "sub_category": "bitcoin",
                "timeframe": "5m",
                "sort": "volume",
                "order": "desc",
            }
            response = self.session.get(endpoint, params=params, timeout=10)
            response.raise_for_status()
            return response.json().get("data", [])
        except Exception as e:
            logger.error(f"Failed to fetch BTC markets: {e}")
            return []

    def get_market_price(self, market_id: str) -> Optional[Dict]:
        """Get current price and spread for a market."""
        try:
            endpoint = f"{self.base_url}/markets/{market_id}/price"
            response = self.session.get(endpoint, timeout=5)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to fetch market price for {market_id}: {e}")
            return None

    def get_market_volume(self, market_id: str) -> Optional[float]:
        """Get 24h trading volume for a market."""
        try:
            endpoint = f"{self.base_url}/markets/{market_id}/volume"
            response = self.session.get(endpoint, timeout=5)
            response.raise_for_status()
            data = response.json()
            return data.get("volume_24h", 0)
        except Exception as e:
            logger.error(f"Failed to fetch volume for {market_id}: {e}")
            return 0

    def place_order(
        self, market_id: str, side: str, amount: float, price: float
    ) -> Optional[Dict]:
        """Place an order (BUY/SELL) on Polymarket."""
        try:
            endpoint = f"{self.base_url}/orders"
            payload = {
                "market_id": market_id,
                "side": side.upper(),  # BUY or SELL
                "amount": amount,
                "price": price,
            }
            response = self.session.post(endpoint, json=payload, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to place order: {e}")
            return None

    def cancel_order(self, order_id: str) -> bool:
        """Cancel an existing order."""
        try:
            endpoint = f"{self.base_url}/orders/{order_id}"
            response = self.session.delete(endpoint, timeout=10)
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            return False

    def get_order_status(self, order_id: str) -> Optional[Dict]:
        """Get status of an order."""
        try:
            endpoint = f"{self.base_url}/orders/{order_id}"
            response = self.session.get(endpoint, timeout=5)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to fetch order status: {e}")
            return None

    def get_balance(self) -> Optional[float]:
        """Get account balance."""
        try:
            endpoint = f"{self.base_url}/account/balance"
            response = self.session.get(endpoint, timeout=5)
            response.raise_for_status()
            return response.json().get("balance", 0)
        except Exception as e:
            logger.error(f"Failed to fetch balance: {e}")
            return None

    def get_open_positions(self) -> List[Dict]:
        """Get all open positions."""
        try:
            endpoint = f"{self.base_url}/account/positions"
            response = self.session.get(endpoint, timeout=5)
            response.raise_for_status()
            return response.json().get("positions", [])
        except Exception as e:
            logger.error(f"Failed to fetch open positions: {e}")
            return []