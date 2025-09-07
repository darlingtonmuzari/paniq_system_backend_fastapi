#!/usr/bin/env python3
"""
Create payment-related database tables and initialize credit tiers
"""
import asyncio
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models.base import Base
from app.models.payment import CreditTier, Invoice, PaymentNotification
from app.services.ozow_service import OzowService


async def create_payment_tables():
    """Create payment tables and initialize credit tiers"""
    
    # Create async engine
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=True,
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW
    )
    
    # Import all models to ensure they're registered
    from app.models import (
        SecurityFirm, CoverageArea, FirmPersonnel, Team,
        RegisteredUser, UserGroup, GroupMobileNumber, UserFine,
        SubscriptionProduct, StoredSubscription, CreditTransaction,
        PanicRequest, ServiceProvider, RequestFeedback, RequestStatusUpdate,
        ResponseTimeMetric, PerformanceAlert, ZonePerformanceReport
    )
    
    # Create tables
    async with engine.begin() as conn:
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
        print("✅ Payment tables created successfully")
    
    # Initialize credit tiers
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        ozow_service = OzowService()
        await ozow_service.initialize_credit_tiers(session)
        print("✅ Credit tiers initialized successfully")
    
    await engine.dispose()
    print("✅ Database setup completed")


if __name__ == "__main__":
    print("🚀 Setting up payment system...")
    print("=" * 50)
    
    try:
        asyncio.run(create_payment_tables())
        print("\n🎉 Payment system setup completed successfully!")
        print("\nCredit Tiers:")
        print("- 0-50 credits: R100.00")
        print("- 51-100 credits: R150.00") 
        print("- 101-500 credits: R600.00")
        print("- 501-1000 credits: R1000.00")
        print("- 1001-5000 credits: R4500.00")
        print("- 5001-10000 credits: R8000.00")
        
    except Exception as e:
        print(f"❌ Error setting up payment system: {str(e)}")
        sys.exit(1)