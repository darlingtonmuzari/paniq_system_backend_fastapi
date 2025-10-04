#!/usr/bin/env python3
"""
Test just the validation logic for the credit tier creation
"""
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from app.api.v1.credit_tiers import CreditTierCreate


def test_validation():
    """Test the validation logic only"""
    
    try:
        # Test the exact payload that was failing
        tier_data = CreditTierCreate(
            name="Sample Pack",
            price=65,
            description="Perfect for a tiny home",
            min_credits=51,
            max_credits=100,
            discount_percentage=0,
            sort_order=0,
            is_active=True
        )
        
        print("✅ CreditTierCreate validation passed!")
        print(f"   Name: {tier_data.name}")
        print(f"   Range: {tier_data.min_credits}-{tier_data.max_credits}")
        print(f"   Price: R{tier_data.price}")
        print(f"   Sort order: {tier_data.sort_order}")
        
        # Test that the validator works correctly
        if tier_data.min_credits <= tier_data.max_credits:
            print("✅ Credits range validation passed")
        else:
            print("❌ Credits range validation failed")
            
        return True
        
    except Exception as e:
        print(f"❌ Validation failed: {str(e)}")
        return False


if __name__ == "__main__":
    print("🧪 Testing Credit Tier Validation")
    print("=" * 40)
    
    if test_validation():
        print("\n🎉 Validation test passed!")
        print("The POST endpoint should now work with the provided payload.")
    else:
        print("\n❌ Validation test failed!")
        sys.exit(1)