#!/usr/bin/env python3
"""
Test S3 connection and create bucket if needed
"""
import boto3
import sys
import os
from botocore.exceptions import ClientError, NoCredentialsError

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.core.config import settings

def test_s3_connection():
    """Test S3 connection and create bucket if needed"""
    
    print("Testing S3 connection...")
    print(f"Bucket: {settings.AWS_S3_BUCKET}")
    print(f"Region: {settings.AWS_REGION_NAME}")
    
    try:
        # Create S3 client
        s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION_NAME
        )
        
        # Test credentials by listing buckets
        print("Testing AWS credentials...")
        response = s3_client.list_buckets()
        print(f"✓ AWS credentials are valid. Found {len(response['Buckets'])} buckets.")
        
        # Check if our bucket exists
        bucket_name = settings.AWS_S3_BUCKET
        bucket_exists = False
        
        for bucket in response['Buckets']:
            if bucket['Name'] == bucket_name:
                bucket_exists = True
                break
        
        if bucket_exists:
            print(f"✓ Bucket '{bucket_name}' already exists.")
        else:
            print(f"✗ Bucket '{bucket_name}' does not exist. Creating...")
            
            # Create bucket
            if settings.AWS_REGION_NAME == 'us-east-1':
                # us-east-1 doesn't need LocationConstraint
                s3_client.create_bucket(Bucket=bucket_name)
            else:
                s3_client.create_bucket(
                    Bucket=bucket_name,
                    CreateBucketConfiguration={'LocationConstraint': settings.AWS_REGION_NAME}
                )
            
            print(f"✓ Bucket '{bucket_name}' created successfully.")
        
        # Test upload/download
        print("Testing file operations...")
        test_key = "test/connection_test.txt"
        test_content = b"S3 connection test successful!"
        
        # Upload test file
        s3_client.put_object(
            Bucket=bucket_name,
            Key=test_key,
            Body=test_content,
            ContentType='text/plain'
        )
        print("✓ Test file uploaded successfully.")
        
        # Download test file
        response = s3_client.get_object(Bucket=bucket_name, Key=test_key)
        downloaded_content = response['Body'].read()
        
        if downloaded_content == test_content:
            print("✓ Test file downloaded successfully.")
        else:
            print("✗ Downloaded content doesn't match uploaded content.")
            return False
        
        # Clean up test file
        s3_client.delete_object(Bucket=bucket_name, Key=test_key)
        print("✓ Test file cleaned up.")
        
        print("\n🎉 S3 connection test completed successfully!")
        return True
        
    except NoCredentialsError:
        print("✗ AWS credentials not found or invalid.")
        print("Please check your AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY.")
        return False
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'BucketAlreadyOwnedByYou':
            print(f"✓ Bucket '{bucket_name}' already exists and is owned by you.")
            return True
        elif error_code == 'BucketAlreadyExists':
            print(f"✗ Bucket '{bucket_name}' already exists but is owned by someone else.")
            print("Please choose a different bucket name.")
            return False
        else:
            print(f"✗ AWS Error: {e}")
            return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = test_s3_connection()
    sys.exit(0 if success else 1)