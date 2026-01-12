import asyncio
import json
import logging
import aiohttp
import time
from eth_account.messages import encode_defunct
from eth_account import Account
from web3 import Web3
from typing import Dict, List, Optional, Any
from utils.rate_limiter import rate_limit_manager
from config.settings import Settings


logger = logging.getLogger(__name__)


class ClobClient:
    """
    Client for interacting with Polymarket's CLOB API.
    """
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.base_url = settings.POLYMARKET_CLOB_API_URL
        self.session = None
        self.account = Account.from_key(settings.PRIVATE_KEY)
        self.web3 = Web3()
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def _sign_message(self, message: str) -> str:
        """
        Sign a message with the private key.
        """
        encoded_msg = encode_defunct(text=message)
        signed_msg = self.web3.eth.account.sign_message(encoded_msg, private_key=self.settings.PRIVATE_KEY)
        return signed_msg.signature.hex()
    
    async def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None, 
                          headers: Optional[Dict] = None) -> Dict:
        """
        Make an authenticated request to the CLOB API.
        """
        if not self.session:
            raise RuntimeError("Client session not initialized. Use 'async with' statement.")
        
        # Apply rate limiting
        await rate_limit_manager.get_limiter(
            "clob_api", 
            self.settings.RATE_LIMIT_REQUESTS, 
            self.settings.RATE_LIMIT_WINDOW
        ).acquire()
        
        url = f"{self.base_url}{endpoint}"
        
        # Prepare headers
        request_headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.settings.L2_API_KEY}",
            "X-Wallet-Signature": self._sign_message(f"{method.upper()}{url}{json.dumps(data) if data else ''}{int(time.time())}")
        }
        
        if headers:
            request_headers.update(headers)
        
        try:
            async with self.session.request(method, url, json=data, headers=request_headers) as response:
                response_text = await response.text()
                
                if response.status != 200:
                    logger.error(f"API request failed: {response.status} - {response_text}")
                    raise Exception(f"API request failed: {response.status} - {response_text}")
                
                return json.loads(response_text)
        except Exception as e:
            logger.error(f"Request error: {e}")
            raise
    
    async def get_markets(self) -> List[Dict]:
        """
        Get all available markets.
        """
        return await self._make_request("GET", "/markets")
    
    async def get_market(self, market_id: str) -> Dict:
        """
        Get details for a specific market.
        """
        return await self._make_request("GET", f"/markets/{market_id}")
    
    async def get_orderbook(self, market_id: str) -> Dict:
        """
        Get the orderbook for a specific market.
        """
        return await self._make_request("GET", f"/markets/{market_id}/orderbook")
    
    async def place_order(self, market_id: str, side: str, price: float, size: float, 
                         order_type: str = "limit") -> Dict:
        """
        Place an order on the CLOB.
        
        :param market_id: ID of the market
        :param side: 'buy' or 'sell'
        :param price: Price at which to place the order
        :param size: Size of the order
        :param order_type: Type of order ('limit', 'market')
        """
        order_data = {
            "marketId": market_id,
            "side": side.lower(),
            "price": str(price),
            "size": str(size),
            "orderType": order_type.lower(),
            "signature": self._sign_message(f"place_order_{market_id}_{side}_{price}_{size}")
        }
        
        return await self._make_request("POST", "/orders", order_data)
    
    async def cancel_order(self, order_id: str) -> Dict:
        """
        Cancel an existing order.
        
        :param order_id: ID of the order to cancel
        """
        cancel_data = {
            "orderId": order_id,
            "signature": self._sign_message(f"cancel_order_{order_id}")
        }
        
        return await self._make_request("DELETE", f"/orders/{order_id}", cancel_data)
    
    async def cancel_all_orders(self, market_id: Optional[str] = None) -> Dict:
        """
        Cancel all orders, optionally for a specific market.
        
        :param market_id: Optional market ID to cancel orders for
        """
        cancel_data = {
            "signature": self._sign_message(f"cancel_all_orders_{market_id or 'all'}")
        }
        
        endpoint = "/orders/all"
        if market_id:
            endpoint += f"?marketId={market_id}"
        
        return await self._make_request("DELETE", endpoint, cancel_data)
    
    async def get_open_orders(self, market_id: Optional[str] = None) -> List[Dict]:
        """
        Get all open orders, optionally for a specific market.
        
        :param market_id: Optional market ID to filter orders
        """
        params = ""
        if market_id:
            params = f"?marketId={market_id}"
        
        return await self._make_request("GET", f"/orders/open{params}")
    
    async def get_order_status(self, order_id: str) -> Dict:
        """
        Get the status of a specific order.
        
        :param order_id: ID of the order to check
        """
        return await self._make_request("GET", f"/orders/{order_id}/status")
    
    async def get_fills(self, market_id: Optional[str] = None) -> List[Dict]:
        """
        Get fills for the account, optionally for a specific market.
        
        :param market_id: Optional market ID to filter fills
        """
        params = ""
        if market_id:
            params = f"?marketId={market_id}"
        
        return await self._make_request("GET", f"/fills{params}")
    
    async def get_balances(self) -> Dict:
        """
        Get account balances.
        """
        return await self._make_request("GET", "/balances")