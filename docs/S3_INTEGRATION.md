# S3 Integration for Document Storage

## Overview

The Paniq System Platform now supports AWS S3 for document storage, providing scalable and reliable file storage for security firm documents.

## Configuration

### Environment Variables

Add the following to your `.env` file:

```bash
# AWS S3 Configuration
AWS_ACCESS_KEY_ID=your-aws-access-key-id
AWS_SECRET_ACCESS_KEY=your-aws-secret-access-key
AWS_REGION_NAME=af-south-1
AWS_S3_BUCKET=paniq-system-dev
USE_S3_STORAGE=true
```

### Fallback Behavior

If AWS credentials are not configured, the system will automatically fall back to local file storage in the `./uploads/` directory.

## Features

### 1. Automatic S3 Upload
- Documents uploaded via `/api/v1/security-firms/{firm_id}/documents` are automatically stored in S3
- Files are organized by firm: `security_firms/{firm_id}/{document_type}_{uuid}.{extension}`
- Original filename and metadata are preserved

### 2. Secure Downloads
- Documents are served via presigned URLs (1-hour expiration)
- Access endpoint: `/api/v1/security-firms/{firm_id}/documents/{document_id}/download`
- Automatic permission checking based on firm membership

### 3. Migration Support
- Existing local documents can be migrated to S3 using `scripts/migrate_documents_to_s3.py`
- Database paths are automatically updated during migration

## S3 Bucket Structure

```
paniq-system-dev/
├── security_firms/
│   ├── {firm_id_1}/
│   │   ├── registration_certificate_{uuid}.pdf
│   │   ├── proof_of_address_{uuid}.pdf
│   │   └── vat_certificate_{uuid}.pdf
│   └── {firm_id_2}/
│       └── registration_certificate_{uuid}.pdf
└── test/
    └── connection_test.txt (temporary test files)
```

## Database Changes

The `firm_documents.file_path` field now stores:
- **S3 files**: S3 key (e.g., `security_firms/123/registration_certificate_456.pdf`)
- **Local files**: Local path (e.g., `uploads/security_firms/123/file.pdf`)

## API Endpoints

### Upload Document
```http
POST /api/v1/security-firms/{firm_id}/documents?document_type={type}
Content-Type: multipart/form-data

file: [binary file data]
```

### Download Document
```http
GET /api/v1/security-firms/{firm_id}/documents/{document_id}/download
```
Returns a redirect to a presigned S3 URL or serves the file directly for local storage.

### List Documents
```http
GET /api/v1/security-firms/{firm_id}/documents
```

## Security Features

1. **Access Control**: Only firm members can upload/download documents
2. **Presigned URLs**: Temporary, secure access to S3 objects
3. **Metadata Preservation**: Original filenames and document types stored as S3 metadata
4. **Permission Validation**: All operations require proper firm membership

## Testing

### Test S3 Connection
```bash
python3 scripts/test_s3_connection.py
```

### Migrate Existing Documents
```bash
python3 scripts/migrate_documents_to_s3.py
```

## Monitoring

- All S3 operations are logged with structured logging
- Failed uploads fall back to local storage with error logging
- Document access is tracked in application logs

## Cost Optimization

- Presigned URLs reduce bandwidth costs
- Files are stored in the configured AWS region for optimal performance
- Standard S3 storage class is used (can be optimized with lifecycle policies)

## Backup Strategy

S3 provides built-in durability (99.999999999%), but additional backup options include:
- Cross-region replication
- Versioning (can be enabled on the bucket)
- Integration with existing backup scripts in `deploy/backup-restore/`

## Troubleshooting

### Common Issues

1. **"AWS credentials not found"**
   - Verify `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` in `.env`
   - Check IAM permissions for S3 access

2. **"Bucket does not exist"**
   - Run `python3 scripts/test_s3_connection.py` to create the bucket
   - Verify bucket name and region configuration

3. **"Failed to generate presigned URL"**
   - Check S3 object exists
   - Verify IAM permissions include `s3:GetObject`

### Required IAM Permissions

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::paniq-system-dev",
                "arn:aws:s3:::paniq-system-dev/*"
            ]
        }
    ]
}
```

## Future Enhancements

- [ ] Implement S3 lifecycle policies for cost optimization
- [ ] Add support for multiple file formats and size validation
- [ ] Implement virus scanning for uploaded files
- [ ] Add document versioning support
- [ ] Integrate with CloudFront for global CDN distribution