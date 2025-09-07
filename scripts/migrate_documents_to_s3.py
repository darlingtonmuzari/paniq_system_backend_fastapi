#!/usr/bin/env python3
"""
Migrate existing local documents to S3 and update database paths
"""
import asyncio
import os
import sys
from pathlib import Path

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.core.database import get_db
from app.models.security_firm import FirmDocument
from app.services.s3_service import S3Service
from app.core.config import settings
from sqlalchemy import select
import boto3

async def migrate_documents_to_s3():
    """Migrate existing local documents to S3"""
    
    print("Starting document migration to S3...")
    
    if not settings.AWS_S3_BUCKET:
        print("❌ AWS S3 bucket not configured. Please set AWS_S3_BUCKET in .env")
        return False
    
    try:
        s3_service = S3Service()
    except Exception as e:
        print(f"❌ Failed to initialize S3 service: {e}")
        return False
    
    # Get database session
    async for db in get_db():
        try:
            # Get all documents with local file paths
            result = await db.execute(
                select(FirmDocument).where(
                    FirmDocument.file_path.like('uploads/%')
                )
            )
            documents = result.scalars().all()
            
            if not documents:
                print("✅ No local documents found to migrate.")
                return True
            
            print(f"Found {len(documents)} documents to migrate...")
            
            migrated_count = 0
            failed_count = 0
            
            for doc in documents:
                try:
                    local_path = doc.file_path
                    
                    # Check if local file exists
                    if not os.path.exists(local_path):
                        print(f"⚠️  Local file not found: {local_path}")
                        failed_count += 1
                        continue
                    
                    # Read local file
                    with open(local_path, 'rb') as f:
                        file_content = f.read()
                    
                    # Generate S3 key
                    firm_id = str(doc.firm_id)
                    file_extension = Path(local_path).suffix
                    s3_key = f"security_firms/{firm_id}/{doc.document_type}_{doc.id}{file_extension}"
                    
                    # Upload to S3
                    s3_service.s3_client.put_object(
                        Bucket=settings.AWS_S3_BUCKET,
                        Key=s3_key,
                        Body=file_content,
                        ContentType=doc.mime_type or 'application/octet-stream',
                        Metadata={
                            'original_filename': doc.file_name,
                            'document_type': doc.document_type,
                            'migrated_from': local_path
                        }
                    )
                    
                    # Update database record
                    doc.file_path = s3_key
                    
                    print(f"✅ Migrated: {local_path} -> s3://{settings.AWS_S3_BUCKET}/{s3_key}")
                    migrated_count += 1
                    
                except Exception as e:
                    print(f"❌ Failed to migrate {doc.file_path}: {e}")
                    failed_count += 1
            
            # Commit all changes
            await db.commit()
            
            print(f"\n📊 Migration Summary:")
            print(f"   ✅ Successfully migrated: {migrated_count}")
            print(f"   ❌ Failed: {failed_count}")
            print(f"   📁 Total processed: {len(documents)}")
            
            if failed_count == 0:
                print("\n🎉 All documents migrated successfully!")
                return True
            else:
                print(f"\n⚠️  Migration completed with {failed_count} failures.")
                return False
                
        except Exception as e:
            print(f"❌ Database error: {e}")
            return False
        finally:
            await db.close()

if __name__ == "__main__":
    success = asyncio.run(migrate_documents_to_s3())
    sys.exit(0 if success else 1)