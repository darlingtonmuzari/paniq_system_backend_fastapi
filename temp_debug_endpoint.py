#!/usr/bin/env python3
"""
Temporary fix: Patch the credit-tiers endpoint to allow viewing all tiers
This creates a backup and temporarily modifies the API for debugging
"""

def create_debug_version():
    """Create a temporary debug version of the credit-tiers API"""
    
    # Read current file
    with open('/home/melcy/Programming/kiro/paniq_system/app/api/v1/credit_tiers.py', 'r') as f:
        content = f.read()
    
    # Create backup
    with open('/home/melcy/Programming/kiro/paniq_system/app/api/v1/credit_tiers_backup.py', 'w') as f:
        f.write(content)
    
    # Find the admin check section and comment it out temporarily
    debug_content = content.replace(
        '''        # Non-admin users: always restricted to active tiers only
        if not is_admin:
            query = query.where(CreditTier.is_active == True)''',
        '''        # Non-admin users: always restricted to active tiers only
        # TEMPORARY DEBUG: Commented out for testing - REMOVE THIS IN PRODUCTION
        # if not is_admin:
        #     query = query.where(CreditTier.is_active == True)'''
    )
    
    # Write debug version
    with open('/home/melcy/Programming/kiro/paniq_system/app/api/v1/credit_tiers_debug.py', 'w') as f:
        f.write(debug_content)
    
    print("Created debug version:")
    print("✓ Backup saved to: credit_tiers_backup.py") 
    print("✓ Debug version created: credit_tiers_debug.py")
    print("\nTo apply the debug version:")
    print("1. cp app/api/v1/credit_tiers_debug.py app/api/v1/credit_tiers.py")
    print("2. Restart your API server")
    print("3. Test the endpoint")
    print("4. Restore: cp app/api/v1/credit_tiers_backup.py app/api/v1/credit_tiers.py")

if __name__ == "__main__":
    create_debug_version()