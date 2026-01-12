import asyncio
import json
import logging
import aiohttp
from eth_account.messages import encode_defunct
from eth_account import Account
from web3 import Web3
from typing import Dict, List, Optional, Any
from utils.rate_limiter import rate_limit_manager
from config.settings import Settings


logger = logging.getLogger(__name__)


class ChainClient:
    """
    Client for interacting with Polymarket's Chain API.
    """
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.base_url = settings.POLYMARKET_CHAIN_API_URL
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
        Make an authenticated request to the Chain API.
        """
        if not self.session:
            raise RuntimeError("Client session not initialized. Use 'async with' statement.")
        
        # Apply rate limiting
        await rate_limit_manager.get_limiter(
            "chain_api", 
            self.settings.RATE_LIMIT_REQUESTS, 
            self.settings.RATE_LIMIT_WINDOW
        ).acquire()
        
        url = f"{self.base_url}{endpoint}"
        
        # Prepare headers
        request_headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.settings.L2_API_KEY}",
        }
        
        if headers:
            request_headers.update(headers)
        
        try:
            async with self.session.request(method, url, json=data, headers=request_headers) as response:
                response_text = await response.text()
                
                if response.status != 200:
                    logger.error(f"Chain API request failed: {response.status} - {response_text}")
                    raise Exception(f"Chain API request failed: {response.status} - {response_text}")
                
                return json.loads(response_text)
        except Exception as e:
            logger.error(f"Chain API request error: {e}")
            raise
    
    async def get_wallet_balance(self) -> Dict:
        """
        Get wallet balance on the blockchain.
        """
        # Using Alchemy's API for balance
        params = {
            "id": 1,
            "jsonrpc": "2.0",
            "method": "eth_getBalance",
            "params": [self.settings.WALLET_ADDRESS, "latest"]
        }
        
        return await self._make_request("POST", "", params)
    
    async def get_transaction_history(self) -> List[Dict]:
        """
        Get transaction history for the wallet.
        """
        # Using Alchemy's API for transaction history
        params = {
            "id": 1,
            "jsonrpc": "2.0",
            "method": "alchemy_getAssetTransfers",
            "params": [{
                "fromBlock": "0x0",
                "toBlock": "latest",
                "fromAddress": self.settings.WALLET_ADDRESS,
                "category": ["external", "internal", "token"],
                "withMetadata": True
            }]
        }
        
        return await self._make_request("POST", "", params)
    
    async def get_gas_price(self) -> Dict:
        """
        Get current gas price on the network.
        """
        params = {
            "id": 1,
            "jsonrpc": "2.0",
            "method": "eth_gasPrice",
            "params": []
        }
        
        return await self._make_request("POST", "", params)
    
    async def estimate_gas(self, transaction: Dict) -> Dict:
        """
        Estimate gas for a transaction.
        
        :param transaction: Transaction object to estimate gas for
        """
        params = {
            "id": 1,
            "jsonrpc": "2.0",
            "method": "eth_estimateGas",
            "params": [transaction]
        }
        
        return await self._make_request("POST", "", params)
    
    async def send_transaction(self, transaction: Dict) -> Dict:
        """
        Send a transaction to the blockchain.
        
        :param transaction: Transaction object to send
        """
        # Sign the transaction
        signed_txn = self.account.sign_transaction(transaction)
        tx_hash = signed_txn.hash.hex()
        
        params = {
            "id": 1,
            "jsonrpc": "2.0",
            "method": "eth_sendRawTransaction",
            "params": [signed_txn.rawTransaction.hex()]
        }
        
        return await self._make_request("POST", "", params)
    
    async def get_block_info(self, block_number: Optional[str] = "latest") -> Dict:
        """
        Get information about a specific block.
        
        :param block_number: Block number to get info for (default: latest)
        """
        params = {
            "id": 1,
            "jsonrpc": "2.0",
            "method": "eth_getBlockByNumber",
            "params": [block_number, True]
        }
        
        return await self._make_request("POST", "", params)
    
    async def get_contract_events(self, contract_address: str, event_signature: str, 
                                from_block: str = "0x0", to_block: str = "latest") -> List[Dict]:
        """
        Get events from a specific contract.
        
        :param contract_address: Address of the contract
        :param event_signature: Signature of the event to query
        :param from_block: Starting block (default: 0x0)
        :param to_block: Ending block (default: latest)
        """
        params = {
            "id": 1,
            "jsonrpc": "2.0",
            "method": "eth_getLogs",
            "params": [{
                "fromBlock": from_block,
                "toBlock": to_block,
                "address": contract_address,
                "topics": [event_signature]
            }]
        }
        
        return await self._make_request("POST", "", params)