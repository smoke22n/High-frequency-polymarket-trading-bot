"""
Conditional Token Framework (CTF) Client for interacting with Gnosis Conditional Tokens
"""
import logging
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from web3 import Web3
from eth_abi import encode
from eth_utils import function_signature_to_4byte_selector
from api_clients.chain_client import ChainClient


class CTFClient:
    """
    Client for interacting with the Gnosis Conditional Tokens Framework (CTF)
    """
    
    def __init__(self, 
                 chain_client: ChainClient,
                 ctf_address: str,
                 collateral_token_address: str,
                 position_proxy_address: str):
        """
        Initialize the CTF Client
        
        Args:
            chain_client: Client for interacting with the blockchain
            ctf_address: Address of the CTF (ConditionalTokens) contract
            collateral_token_address: Address of the collateral token (USDC)
            position_proxy_address: Address of the position proxy contract
        """
        self.chain_client = chain_client
        self.ctf_address = ctf_address
        self.collateral_token_address = collateral_token_address
        self.position_proxy_address = position_proxy_address
        self.logger = logging.getLogger(__name__)
        
        # Initialize Web3 instance
        self.w3 = Web3()
    
    async def prepare_condition(self, 
                               oracle_address: str, 
                               payout_denominator: int, 
                               num_outcomes: int) -> Dict:
        """
        Prepare a condition in the CTF
        
        Args:
            oracle_address: Address of the oracle that will resolve the condition
            payout_denominator: Total number of outcome slots (typically 2 for YES/NO)
            num_outcomes: Number of possible outcomes (typically 2 for YES/NO)
            
        Returns:
            Transaction result dictionary
        """
        try:
            # Prepare the function call data for prepareCondition
            function_signature = "prepareCondition(address,address,uint256,uint256)"
            selector = function_signature_to_4byte_selector(function_signature)
            
            # Encode the parameters
            encoded_params = encode(
                ['address', 'address', 'uint256', 'uint256'],
                [oracle_address, self.collateral_token_address, payout_denominator, num_outcomes]
            )
            
            call_data = selector.hex() + encoded_params.hex()
            
            # Execute via proxy
            result = await self.chain_client.execute_via_proxy(
                proxy_address=self.position_proxy_address,
                target_contract=self.ctf_address,
                function_name="prepareCondition",
                params={
                    "oracle": oracle_address,
                    "collateralToken": self.collateral_token_address,
                    "payoutDenominator": payout_denominator,
                    "numOutcomes": num_outcomes,
                    "callData": call_data
                }
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error preparing condition: {str(e)}")
            return {"success": False, "message": str(e)}
    
    async def split_position(self,
                            condition_id: str,
                            partition: List[int],
                            amount: int) -> Dict:
        """
        Split collateral into conditional tokens based on a condition

        Args:
            condition_id: ID of the prepared condition
            partition: Partition of outcome slot counts (e.g., [1, 1] for equal YES/NO)
            amount: Amount of collateral to split

        Returns:
            Transaction result dictionary
        """
        try:
            # Prepare the function call data for splitPosition
            function_signature = "splitPosition(address,address,bytes32,uint256[],uint256)"
            selector = function_signature_to_4byte_selector(function_signature)

            # Encode the parameters
            encoded_params = encode(
                ['address', 'address', 'bytes32', 'uint256[]', 'uint256'],
                [self.collateral_token_address, "0x0000000000000000000000000000000000000000", condition_id, partition, amount]
            )

            call_data = selector.hex() + encoded_params.hex()

            # Execute via proxy
            result = await self.chain_client.execute_via_proxy(
                proxy_address=self.position_proxy_address,
                target_contract=self.ctf_address,
                function_name="splitPosition",
                params={
                    "collateralToken": self.collateral_token_address,
                    "parentCollectionId": "0x0000000000000000000000000000000000000000000000000000000000000000",  # Root collection
                    "conditionId": condition_id,
                    "partition": partition,
                    "amount": amount,
                    "callData": call_data
                }
            )

            return result

        except Exception as e:
            self.logger.error(f"Error splitting position: {str(e)}")
            return {"success": False, "message": str(e)}
    
    async def merge_positions(self,
                             condition_id: str,
                             partition: List[int],
                             amount: int) -> Dict:
        """
        Merge conditional tokens back into collateral

        Args:
            condition_id: ID of the prepared condition
            partition: Partition of outcome slot counts (e.g., [1, 1] for equal YES/NO)
            amount: Amount of each conditional token to merge

        Returns:
            Transaction result dictionary
        """
        try:
            # Prepare the function call data for mergePositions
            function_signature = "mergePositions(address,address,bytes32,uint256[],uint256)"
            selector = function_signature_to_4byte_selector(function_signature)

            # Encode the parameters
            encoded_params = encode(
                ['address', 'address', 'bytes32', 'uint256[]', 'uint256'],
                [self.collateral_token_address, "0x0000000000000000000000000000000000000000", condition_id, partition, amount]
            )

            call_data = selector.hex() + encoded_params.hex()

            # Execute via proxy
            result = await self.chain_client.execute_via_proxy(
                proxy_address=self.position_proxy_address,
                target_contract=self.ctf_address,
                function_name="mergePositions",
                params={
                    "collateralToken": self.collateral_token_address,
                    "parentCollectionId": "0x0000000000000000000000000000000000000000000000000000000000000000",  # Root collection
                    "conditionId": condition_id,
                    "partition": partition,
                    "amount": amount,
                    "callData": call_data
                }
            )

            return result

        except Exception as e:
            self.logger.error(f"Error merging positions: {str(e)}")
            return {"success": False, "message": str(e)}
    
    async def redeem_positions(self, 
                              condition_id: str, 
                              index_sets: List[int]) -> Dict:
        """
        Redeem conditional tokens after a condition has been resolved
        
        Args:
            condition_id: ID of the resolved condition
            index_sets: Index sets that represent which outcomes to redeem
            
        Returns:
            Transaction result dictionary
        """
        try:
            # Prepare the function call data for redeemPositions
            function_signature = "redeemPositions(IERC20,address,bytes32,uint256[])"
            selector = function_signature_to_4byte_selector(function_signature)
            
            # Encode the parameters
            encoded_params = encode(
                ['address', 'address', 'bytes32', 'uint256[]'],
                [self.collateral_token_address, self.position_proxy_address, condition_id, index_sets]
            )
            
            call_data = selector.hex() + encoded_params.hex()
            
            # Execute via proxy
            result = await self.chain_client.execute_via_proxy(
                proxy_address=self.position_proxy_address,
                target_contract=self.ctf_address,
                function_name="redeemPositions",
                params={
                    "collateralToken": self.collateral_token_address,
                    "parentCollectionId": "0x0000000000000000000000000000000000000000000000000000000000000000",  # Root collection
                    "conditionId": condition_id,
                    "indexSets": index_sets,
                    "callData": call_data
                }
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error redeeming positions: {str(e)}")
            return {"success": False, "message": str(e)}
    
    def calculate_collection_id(self, parent_collection_id: str, condition_id: str, index_set: int) -> str:
        """
        Calculate the collection ID for a specific condition and index set
        
        Args:
            parent_collection_id: Parent collection ID
            condition_id: Condition ID
            index_set: Index set (e.g., 1 for YES, 2 for NO in a binary outcome)
            
        Returns:
            Collection ID as a hex string
        """
        # Hash the inputs to generate the collection ID
        combined_input = parent_collection_id + condition_id[2:] + format(index_set, '064x')
        collection_id = self.w3.keccak(hexstr=combined_input).hex()
        return collection_id