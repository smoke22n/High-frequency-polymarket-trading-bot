"""
Test suite for PositionManager with CTF hedging functionality
"""
import asyncio
import unittest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from api_clients.ctf_client import CTFClient
from api_clients.clob_client import CLOBClient
from utils.position_manager import PositionManager


class TestPositionManager(unittest.TestCase):
    def setUp(self):
        # Mock clients
        self.mock_ctf_client = AsyncMock(spec=CTFClient)
        self.mock_clob_client = MagicMock(spec=CLOBClient)
        
        # Initialize PositionManager with mock clients
        self.position_manager = PositionManager(
            ctf_client=self.mock_ctf_client,
            clob_client=self.mock_clob_client,
            market_id="test_market",
            condition_id="test_condition",
            collateral_token_address="0x1234567890",
            position_proxy_address="0xabcdef1234567890"
        )
    
    def test_initial_balances(self):
        """Test that initial balances are zero"""
        self.assertEqual(self.position_manager.yes_balance, Decimal('0'))
        self.assertEqual(self.position_manager.no_balance, Decimal('0'))
        self.assertEqual(self.position_manager.collateral_balance, Decimal('0'))
    
    def test_update_position_yes(self):
        """Test updating YES position"""
        self.position_manager.update_position('YES', Decimal('100'))
        self.assertEqual(self.position_manager.yes_balance, Decimal('100'))
        self.assertEqual(self.position_manager.no_balance, Decimal('0'))
    
    def test_update_position_no(self):
        """Test updating NO position"""
        self.position_manager.update_position('NO', Decimal('50'))
        self.assertEqual(self.position_manager.yes_balance, Decimal('0'))
        self.assertEqual(self.position_manager.no_balance, Decimal('50'))
    
    def test_update_position_invalid_outcome(self):
        """Test updating with invalid outcome raises error"""
        with self.assertRaises(ValueError):
            self.position_manager.update_position('INVALID', Decimal('100'))
    
    def test_get_available_hedge_amount(self):
        """Test calculating available hedge amount"""
        self.position_manager.yes_balance = Decimal('100')
        self.position_manager.no_balance = Decimal('80')
        self.assertEqual(self.position_manager.get_available_hedge_amount(), Decimal('80'))
        
        self.position_manager.yes_balance = Decimal('50')
        self.position_manager.no_balance = Decimal('75')
        self.assertEqual(self.position_manager.get_available_hedge_amount(), Decimal('50'))
    
    def test_can_merge_true(self):
        """Test can_merge returns True when both positions exist"""
        self.position_manager.yes_balance = Decimal('100')
        self.position_manager.no_balance = Decimal('80')
        self.assertTrue(self.position_manager.can_merge())
    
    def test_can_merge_false(self):
        """Test can_merge returns False when one position is zero"""
        self.position_manager.yes_balance = Decimal('100')
        self.position_manager.no_balance = Decimal('0')
        self.assertFalse(self.position_manager.can_merge())
        
        self.position_manager.yes_balance = Decimal('0')
        self.position_manager.no_balance = Decimal('80')
        self.assertFalse(self.position_manager.can_merge())
    
    def test_get_position_summary(self):
        """Test getting position summary"""
        self.position_manager.yes_balance = Decimal('100')
        self.position_manager.no_balance = Decimal('80')
        self.position_manager.collateral_balance = Decimal('20')
        
        summary = self.position_manager.get_position_summary()
        
        self.assertEqual(summary['market_id'], 'test_market')
        self.assertEqual(summary['yes_balance'], Decimal('100'))
        self.assertEqual(summary['no_balance'], Decimal('80'))
        self.assertEqual(summary['collateral_balance'], Decimal('20'))
        self.assertEqual(summary['hedgeable_amount'], Decimal('80'))
        self.assertEqual(summary['net_exposure'], Decimal('20'))


class TestAsyncPositionManager(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Mock clients
        self.mock_ctf_client = AsyncMock(spec=CTFClient)
        self.mock_clob_client = MagicMock(spec=CLOBClient)
        
        # Initialize PositionManager with mock clients
        self.position_manager = PositionManager(
            ctf_client=self.mock_ctf_client,
            clob_client=self.mock_clob_client,
            market_id="test_market",
            condition_id="test_condition",
            collateral_token_address="0x1234567890",
            position_proxy_address="0xabcdef1234567890"
        )
    
    async def test_merge_positions_success(self):
        """Test successful position merge"""
        # Set up initial positions
        self.position_manager.yes_balance = Decimal('100')
        self.position_manager.no_balance = Decimal('80')
        
        # Mock the CTF client merge_positions method
        mock_result = {
            "success": True,
            "transaction_hash": "0x1234567890abcdef",
        }
        self.mock_ctf_client.merge_positions.return_value = mock_result
        
        # Perform merge
        result = self.position_manager.merge_positions(Decimal('80'))
        
        # Verify the result
        self.assertTrue(result['success'])
        self.assertEqual(result['amount_merged'], Decimal('80'))
        self.assertEqual(result['transaction_hash'], "0x1234567890abcdef")
        
        # Verify balances were updated
        self.assertEqual(self.position_manager.yes_balance, Decimal('20'))
        self.assertEqual(self.position_manager.no_balance, Decimal('0'))
        self.assertEqual(self.position_manager.collateral_balance, Decimal('80'))
        
        # Verify CTF client was called with correct parameters
        self.mock_ctf_client.merge_positions.assert_called_once_with(
            condition_id="test_condition",
            partition=[1, 2],
            amount=80000000  # 80 * 10^6 (assuming 6 decimals)
        )
    
    async def test_merge_positions_partial(self):
        """Test merging partial positions"""
        # Set up initial positions
        self.position_manager.yes_balance = Decimal('50')
        self.position_manager.no_balance = Decimal('30')
        
        # Mock the CTF client merge_positions method
        mock_result = {
            "success": True,
            "transaction_hash": "0x1234567890abcdef",
        }
        self.mock_ctf_client.merge_positions.return_value = mock_result
        
        # Perform merge (should merge 30, the minimum)
        result = self.position_manager.merge_positions()
        
        # Verify the result
        self.assertTrue(result['success'])
        self.assertEqual(result['amount_merged'], Decimal('30'))
        
        # Verify balances were updated
        self.assertEqual(self.position_manager.yes_balance, Decimal('20'))
        self.assertEqual(self.position_manager.no_balance, Decimal('0'))
        self.assertEqual(self.position_manager.collateral_balance, Decimal('30'))
    
    async def test_split_collateral_success(self):
        """Test successful collateral split"""
        # Set up initial positions
        self.position_manager.collateral_balance = Decimal('100')
        
        # Mock the CTF client split_position method
        mock_result = {
            "success": True,
            "transaction_hash": "0xabcdef1234567890",
        }
        self.mock_ctf_client.split_position.return_value = mock_result
        
        # Perform split
        result = self.position_manager.split_collateral(Decimal('50'))
        
        # Verify the result
        self.assertTrue(result['success'])
        self.assertEqual(result['amount_split'], Decimal('50'))
        self.assertEqual(result['transaction_hash'], "0xabcdef1234567890")
        
        # Verify balances were updated
        self.assertEqual(self.position_manager.collateral_balance, Decimal('50'))
        self.assertEqual(self.position_manager.yes_balance, Decimal('50'))
        self.assertEqual(self.position_manager.no_balance, Decimal('50'))
        
        # Verify CTF client was called with correct parameters
        self.mock_ctf_client.split_position.assert_called_once_with(
            condition_id="test_condition",
            partition=[1, 2],
            amount=50000000  # 50 * 10^6 (assuming 6 decimals)
        )


if __name__ == '__main__':
    unittest.main()