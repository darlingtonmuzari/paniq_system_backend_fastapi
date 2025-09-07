"""
S3 service for file storage operations
"""
import boto3
import uuid
from typing import Optional
from fastapi import UploadFile
from botocore.exceptions import ClientError, NoCredentialsError
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class S3Service:
    """Service for handling S3 file operations"""
    
    def __init__(self):
        """Initialize S3 client"""
        if not all([settings.AWS_ACCESS_KEY_ID, settings.AWS_SECRET_ACCESS_KEY, settings.AWS_S3_BUCKET]):
            raise ValueError("AWS credentials and S3 bucket must be configured")
            
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION_NAME
        )
        self.bucket_name = settings.AWS_S3_BUCKET
        
    async def upload_file(
        self,
        file: UploadFile,
        key_prefix: str,
        document_type: str
    ) -> tuple[str, int]:
        """
        Upload file to S3 and return the S3 key and file size
        
        Args:
            file: The uploaded file
            key_prefix: Prefix for the S3 key (e.g., "security_firms/firm_id")
            document_type: Type of document for naming
            
        Returns:
            Tuple of (s3_key, file_size)
        """
        try:
            # Read file content
            content = await file.read()
            file_size = len(content)
            
            # Generate unique S3 key
            file_extension = file.filename.split('.')[-1] if '.' in file.filename else 'bin'
            unique_filename = f"{document_type}_{uuid.uuid4()}.{file_extension}"
            s3_key = f"{key_prefix}/{unique_filename}"
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=content,
                ContentType=file.content_type or 'application/octet-stream',
                Metadata={
                    'original_filename': file.filename,
                    'document_type': document_type
                }
            )
            
            logger.info(f"Successfully uploaded file to S3: {s3_key}")
            return s3_key, file_size
            
        except NoCredentialsError:
            logger.error("AWS credentials not found")
            raise ValueError("AWS credentials not configured")
        except ClientError as e:
            logger.error(f"Failed to upload file to S3: {e}")
            raise ValueError(f"Failed to upload file: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error uploading to S3: {e}")
            raise ValueError(f"Failed to upload file: {str(e)}")
    
    def get_file_url(self, s3_key: str, expires_in: int = 3600) -> str:
        """
        Generate a presigned URL for file access
        
        Args:
            s3_key: The S3 key of the file
            expires_in: URL expiration time in seconds (default 1 hour)
            
        Returns:
            Presigned URL for file access
        """
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': s3_key},
                ExpiresIn=expires_in
            )
            return url
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            raise ValueError(f"Failed to generate file URL: {str(e)}")
    
    def delete_file(self, s3_key: str) -> bool:
        """
        Delete file from S3
        
        Args:
            s3_key: The S3 key of the file to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            logger.info(f"Successfully deleted file from S3: {s3_key}")
            return True
        except ClientError as e:
            logger.error(f"Failed to delete file from S3: {e}")
            return False
    
    def file_exists(self, s3_key: str) -> bool:
        """
        Check if file exists in S3
        
        Args:
            s3_key: The S3 key to check
            
        Returns:
            True if file exists, False otherwise
        """
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except ClientError:
            return False