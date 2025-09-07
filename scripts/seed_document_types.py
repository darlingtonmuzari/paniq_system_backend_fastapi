#!/usr/bin/env python3
"""
Seed script for document types
"""
import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.services.document_type import DocumentTypeService


async def seed_document_types():
    """Seed the database with default document types"""
    
    # Create async engine and session
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        service = DocumentTypeService(session)
        
        # Get or create system admin user
        from app.models.user import RegisteredUser
        from sqlalchemy import select
        
        # Try to find an admin user
        admin_result = await session.execute(
            select(RegisteredUser).where(RegisteredUser.role == "admin").limit(1)
        )
        admin_user = admin_result.scalar_one_or_none()
        
        if not admin_user:
            # Create a system admin user for seeding
            import uuid
            from datetime import datetime
            
            admin_user = RegisteredUser(
                id=uuid.uuid4(),
                email="system@paniq.co.za",
                phone="+27000000000",
                first_name="System",
                last_name="Administrator",
                role="admin",
                is_verified=True,
                password_hash="system_seeded_user"  # This user cannot login
            )
            session.add(admin_user)
            await session.flush()  # Get the ID
            print(f"Created system admin user: {admin_user.email}")
        
        admin_id = str(admin_user.id)
        
        # Define default document types
        document_types = [
            {
                "code": "registration_certificate",
                "name": "Company Registration Certificate",
                "description": "Official company registration certificate from CIPC or relevant authority",
                "is_required": True
            },
            {
                "code": "proof_of_address",
                "name": "Proof of Business Address",
                "description": "Municipal rates bill, lease agreement, or utility bill showing business address",
                "is_required": True
            },
            {
                "code": "vat_certificate",
                "name": "VAT Registration Certificate",
                "description": "VAT registration certificate from SARS (if applicable)",
                "is_required": False
            },
            {
                "code": "insurance_certificate",
                "name": "Professional Indemnity Insurance",
                "description": "Current professional indemnity insurance certificate",
                "is_required": True
            },
            {
                "code": "security_license",
                "name": "Security Industry License",
                "description": "Valid security industry license from PSIRA or relevant authority",
                "is_required": True
            },
            {
                "code": "bank_statement",
                "name": "Bank Statement",
                "description": "Recent bank statement (last 3 months)",
                "is_required": False
            },
            {
                "code": "tax_clearance",
                "name": "Tax Clearance Certificate",
                "description": "Valid tax clearance certificate from SARS",
                "is_required": False
            },
            {
                "code": "identity_document",
                "name": "Identity Document",
                "description": "South African ID document or passport",
                "is_required": True
            },
            {
                "code": "proof_of_residence",
                "name": "Proof of Residence",
                "description": "Municipal rates bill, utility bill, or bank statement (last 3 months)",
                "is_required": True
            },
            {
                "code": "psira_certificate",
                "name": "PSIRA Certificate",
                "description": "Valid PSIRA registration certificate for security personnel",
                "is_required": False
            },
            {
                "code": "annual_return",
                "name": "Annual Return",
                "description": "Company annual return filed with CIPC",
                "is_required": False
            },
            {
                "code": "bee_certificate",
                "name": "B-BBEE Certificate",
                "description": "Broad-Based Black Economic Empowerment certificate",
                "is_required": False
            }
        ]
        
        # Create document types
        created_count = 0
        for doc_data in document_types:
            try:
                existing = await service.get_document_type_by_code(doc_data["code"])
                if existing:
                    print(f"Document type '{doc_data['code']}' already exists, skipping...")
                    continue
                
                await service.create_document_type(created_by=admin_id, **doc_data)
                print(f"Created document type: {doc_data['name']} ({doc_data['code']})")
                created_count += 1
                
            except Exception as e:
                print(f"Error creating document type '{doc_data['code']}': {str(e)}")
        
        print(f"\nSeeding completed! Created {created_count} new document types.")
    
    await engine.dispose()


if __name__ == "__main__":
    print("Seeding document types...")
    asyncio.run(seed_document_types())