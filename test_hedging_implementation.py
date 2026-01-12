"""
Simple integration test to verify the hedging mechanism implementation
"""
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath('.'))

def test_imports():
    """Test that all modules can be imported without errors"""
    try:
        from utils.position_manager import PositionManager
        print("✓ PositionManager imported successfully")
        
        from api_clients.ctf_client import CTFClient
        print("✓ CTFClient imported successfully")
        
        from api_clients.chain_client import ChainClient
        print("✓ ChainClient imported successfully")
        
        from api_clients.clob_client import CLOBClient
        print("✓ CLOBClient imported successfully")
        
        from config.settings import Settings
        print("✓ Settings imported successfully")
        
        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

def test_position_manager_creation():
    """Test that PositionManager can be instantiated"""
    try:
        from api_clients.ctf_client import CTFClient
        from api_clients.clob_client import CLOBClient
        from utils.position_manager import PositionManager
        from unittest.mock import MagicMock
        
        # Create mock clients
        mock_ctf_client = MagicMock(spec=CTFClient)
        mock_clob_client = MagicMock(spec=CLOBClient)
        
        # Create PositionManager instance
        pm = PositionManager(
            ctf_client=mock_ctf_client,
            clob_client=mock_clob_client,
            market_id="test_market",
            condition_id="test_condition",
            collateral_token_address="0x1234567890",
            position_proxy_address="0xabcdef1234567890"
        )
        
        print("✓ PositionManager instantiated successfully")
        print(f"✓ Market ID: {pm.market_id}")
        print(f"✓ Initial YES balance: {pm.yes_balance}")
        print(f"✓ Initial NO balance: {pm.no_balance}")
        
        return True
    except Exception as e:
        print(f"✗ PositionManager creation error: {e}")
        return False

def test_position_updates():
    """Test position update functionality"""
    try:
        from api_clients.ctf_client import CTFClient
        from api_clients.clob_client import CLOBClient
        from utils.position_manager import PositionManager
        from unittest.mock import MagicMock
        from decimal import Decimal
        
        # Create mock clients
        mock_ctf_client = MagicMock(spec=CTFClient)
        mock_clob_client = MagicMock(spec=CLOBClient)
        
        # Create PositionManager instance
        pm = PositionManager(
            ctf_client=mock_ctf_client,
            clob_client=mock_clob_client,
            market_id="test_market",
            condition_id="test_condition",
            collateral_token_address="0x1234567890",
            position_proxy_address="0xabcdef1234567890"
        )
        
        # Test updating positions
        pm.update_position('YES', Decimal('100'))
        assert pm.yes_balance == Decimal('100'), f"Expected 100, got {pm.yes_balance}"
        
        pm.update_position('NO', Decimal('80'))
        assert pm.no_balance == Decimal('80'), f"Expected 80, got {pm.no_balance}"
        
        # Test calculating hedgeable amount
        hedgeable = pm.get_available_hedge_amount()
        assert hedgeable == Decimal('80'), f"Expected 80, got {hedgeable}"
        
        print("✓ Position updates work correctly")
        print(f"✓ YES balance: {pm.yes_balance}")
        print(f"✓ NO balance: {pm.no_balance}")
        print(f"✓ Hedgeable amount: {hedgeable}")
        
        return True
    except Exception as e:
        print(f"✗ Position update test error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("Testing Hedging Mechanism Implementation")
    print("=" * 50)
    
    tests = [
        ("Import Test", test_imports),
        ("Position Manager Creation", test_position_manager_creation),
        ("Position Updates", test_position_updates)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\nRunning {test_name}...")
        result = test_func()
        results.append((test_name, result))
    
    print("\n" + "=" * 50)
    print("Test Results:")
    all_passed = True
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{test_name}: {status}")
        if not result:
            all_passed = False
    
    print(f"\nOverall: {'ALL TESTS PASSED' if all_passed else 'SOME TESTS FAILED'}")
    return all_passed

if __name__ == "__main__":
    success = main()
    if success:
        print("\n✓ Hedging mechanism implementation is working correctly!")
    else:
        print("\n✗ There are issues with the implementation.")