#!/usr/bin/env python3

try:
    print("Testing imports...")
    
    print("1. Testing basic imports...")
    import asyncio
    import secrets
    import string
    from datetime import datetime, timedelta
    from typing import Optional, Dict, Any
    print("   Basic imports OK")
    
    print("2. Testing SQLAlchemy imports...")
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy import select, update, and_
    print("   SQLAlchemy imports OK")
    
    print("3. Testing app imports...")
    from app.core.redis import get_redis
    print("   Redis import OK")
    
    from app.core.config import settings
    print("   Config import OK")
    
    from app.models.user import RegisteredUser
    print("   User model import OK")
    
    from app.models.security_firm import SecurityFirm
    print("   SecurityFirm model import OK")
    
    print("4. Testing full module import...")
    import app.services.account_security
    print("   Module import OK")
    
    print("5. Testing class import...")
    from app.services.account_security import AccountSecurityService
    print("   Class import OK")
    
    print("All imports successful!")
    
except Exception as e:
    print(f"Import failed: {e}")
    import traceback
    traceback.print_exc()