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

    async def execute_via_proxy(self, proxy_address: str, target_contract: str,
                              function_name: str, params: Dict) -> Dict:
        """
        Execute a transaction via a proxy contract to minimize gas costs.

        :param proxy_address: Address of the proxy contract
        :param target_contract: Target contract identifier
        :param function_name: Function to call on the target contract
        :param params: Parameters for the function call
        """
        try:
            # Construct the transaction data for the proxy call
            transaction_data = {
                "from": self.settings.WALLET_ADDRESS,
                "to": proxy_address,
                "data": self._construct_proxy_call_data(target_contract, function_name, params),
                "gas": "0x5208",  # 21000 gas (standard for simple transfers)
                "gasPrice": await self._get_current_gas_price(),
            }

            # Estimate gas for the transaction
            estimated_gas = await self.estimate_gas(transaction_data)
            transaction_data["gas"] = hex(int(estimated_gas.get("result", "0x5208"), 16) * 120 // 100)  # Add 20% buffer

            # Send the transaction
            result = await self.send_transaction(transaction_data)

            return {
                "success": True,
                "transaction_hash": result.get("result"),
                "proxy_address": proxy_address,
                "target_contract": target_contract,
                "function_called": function_name
            }

        except Exception as e:
            logger.error(f"Error executing transaction via proxy: {str(e)}")
            return {
                "success": False,
                "message": str(e),
                "proxy_address": proxy_address,
                "target_contract": target_contract,
                "function_called": function_name
            }

    def _construct_proxy_call_data(self, target_contract: str, function_name: str, params: Dict) -> str:
        """
        Construct the calldata for a proxy contract call.

        :param target_contract: Target contract identifier
        :param function_name: Function to call on the target contract
        :param params: Parameters for the function call
        :return: Hex-encoded calldata string
        """
        # This is a simplified version - in practice, you'd use ABI encoding
        # to properly encode the function signature and parameters
        import hashlib

        # Create function signature hash (first 4 bytes of keccak256 of function signature)
        func_sig = f"{function_name}({','.join(['uint256'] * len(params))})"  # Simplified assumption
        selector = hashlib.sha256(func_sig.encode()).hexdigest()[:8]

        # Encode parameters (this is a simplified version)
        encoded_params = ""
        for param_value in params.values():
            # Convert to hex with padding to 32 bytes
            hex_param = hex(param_value if isinstance(param_value, int) else int(str(param_value))) if param_value else "0"
            encoded_params += hex_param[2:].zfill(64)  # Pad to 32 bytes (64 hex chars)

        return "0x" + selector + encoded_params

    async def _get_current_gas_price(self) -> str:
        """
        Helper method to get current gas price.

        :return: Gas price in hex format
        """
        try:
            gas_price_response = await self.get_gas_price()
            return gas_price_response.get("result", "0x12a05f200")  # Default to ~5 gwei if not available
        except:
            return "0x12a05f200"  # Default to ~5 gwei