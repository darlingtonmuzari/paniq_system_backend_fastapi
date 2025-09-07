# Application Details API Documentation

## Overview
The Application Details API provides comprehensive views of security firm applications, including all associated information such as applicant details, firm information, document status, and more.

## Endpoints

### 1. Get Application Details
**GET** `/api/v1/applications/{APPLICATION_ID}/details`

Returns complete application information including all associated data.

#### Response Structure
```json
{
  "id": "application-uuid",
  "status": "draft|submitted|under_review|approved|rejected",
  "submitted_at": "2025-01-09T12:00:00Z",
  "reviewed_at": "2025-01-09T14:00:00Z",
  "reviewed_by": "reviewer-user-id",
  "reviewer_name": "John Doe",
  "rejection_reason": "Missing documents",
  "admin_notes": "Additional notes",
  "created_at": "2025-01-09T10:00:00Z",
  "updated_at": "2025-01-09T15:00:00Z",
  
  "firm": {
    "id": "firm-uuid",
    "name": "Security Company Ltd",
    "registration_number": "REG123456",
    "email": "contact@security.com",
    "phone": "+27123456789",
    "address": "123 Main St, City",
    "province": "Gauteng",
    "country": "South Africa",
    "vat_number": "VAT123456",
    "verification_status": "submitted",
    "credit_balance": 1000,
    "is_locked": false,
    "created_at": "2025-01-01T00:00:00Z",
    "updated_at": "2025-01-09T12:00:00Z"
  },
  
  "applicant": {
    "user_id": "user-uuid",
    "email": "admin@security.com",
    "first_name": "John",
    "last_name": "Doe",
    "phone": "+27987654321",
    "role": "firm_admin",
    "joined_at": "2025-01-01T00:00:00Z"
  },
  
  "firm_users": [
    {
      "user_id": "user-uuid",
      "email": "admin@security.com",
      "first_name": "John",
      "last_name": "Doe",
      "phone": "+27987654321",
      "role": "firm_admin",
      "status": "active",
      "invited_at": "2025-01-01T00:00:00Z",
      "accepted_at": "2025-01-01T01:00:00Z"
    }
  ],
  
  "required_documents": [
    {
      "code": "registration_certificate",
      "name": "Company Registration Certificate",
      "description": "Official company registration document",
      "is_uploaded": true,
      "uploaded_document": {
        "id": "doc-uuid",
        "document_type": "registration_certificate",
        "document_type_name": "Company Registration Certificate",
        "file_name": "registration.pdf",
        "file_size": 1024000,
        "mime_type": "application/pdf",
        "is_verified": false,
        "verified_by": null,
        "verified_at": null,
        "uploaded_at": "2025-01-09T11:00:00Z",
        "download_url": "https://s3.amazonaws.com/bucket/path/to/file"
      }
    }
  ],
  
  "all_documents": [
    {
      "id": "doc-uuid",
      "document_type": "registration_certificate",
      "document_type_name": "Company Registration Certificate",
      "file_name": "registration.pdf",
      "file_size": 1024000,
      "mime_type": "application/pdf",
      "is_verified": false,
      "verified_by": null,
      "verified_at": null,
      "uploaded_at": "2025-01-09T11:00:00Z",
      "download_url": "https://s3.amazonaws.com/bucket/path/to/file"
    }
  ],
  
  "summary": {
    "total_required_documents": 1,
    "uploaded_required_documents": 1,
    "missing_required_documents": 0,
    "total_documents": 3,
    "verified_documents": 0,
    "unverified_documents": 3,
    "completion_percentage": 100.0,
    "total_firm_users": 1,
    "active_firm_users": 1,
    "can_submit": true
  }
}
```

### 2. Get Application Summary
**GET** `/api/v1/applications/{APPLICATION_ID}/summary`

Returns a quick summary of application status and key metrics.

#### Response Structure
```json
{
  "application_id": "application-uuid",
  "status": "draft",
  "submitted_at": null,
  "reviewed_at": null,
  "total_documents": 3,
  "verified_documents": 0,
  "total_required_documents": 1,
  "uploaded_required_documents": 1,
  "missing_required_documents": 0,
  "completion_percentage": 100.0,
  "can_submit": true,
  "is_complete": true
}
```

## Authorization

### Admin Users
- Can view details for any application
- Have full access to all information including admin notes and reviewer details

### Regular Users (Firm Members)
- Can only view applications for firms they are associated with
- Must have an active association with the firm
- See the same detailed information as admins for their own applications

## Use Cases

### 1. Admin Review Dashboard
Use the detailed endpoint to show comprehensive application information for admin review:
- Complete firm profile
- All uploaded documents with download links
- Document verification status
- Application timeline and notes

### 2. Firm Application Status
Use the summary endpoint for quick status checks:
- Overall completion percentage
- Missing document count
- Submission eligibility

### 3. Document Management
The detailed view provides:
- List of all required documents
- Upload status for each requirement
- Download links for all documents
- Document verification status

## Example Usage

### JavaScript/TypeScript
```javascript
// Get application details
const response = await fetch('/api/v1/applications/APP-UUID/details', {
  headers: {
    'Authorization': 'Bearer your-jwt-token'
  }
});
const applicationDetails = await response.json();

// Check if application is ready for submission
if (applicationDetails.summary.can_submit) {
  console.log('Application is ready for submission');
}

// List missing documents
const missingDocs = applicationDetails.required_documents
  .filter(doc => !doc.is_uploaded)
  .map(doc => doc.name);

console.log('Missing documents:', missingDocs);
```

### Python
```python
import requests

# Get application summary
response = requests.get(
    f'/api/v1/applications/{APPLICATION_ID}/summary',
    headers={'Authorization': f'Bearer {jwt_token}'}
)
summary = response.json()

print(f"Completion: {summary['completion_percentage']}%")
print(f"Can submit: {summary['can_submit']}")
```

## Error Responses

### 404 Not Found
```json
{
  "detail": "Application not found"
}
```

### 403 Forbidden
```json
{
  "detail": "Not authorized to access this application"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Failed to get application details"
}
```

## Features

### ✅ Complete Application Information
- Application status and timeline
- Firm details and verification status
- Applicant information
- All firm users and their roles

### ✅ Document Management
- Required document checklist
- Upload status for each requirement
- All uploaded documents with metadata
- Download links (S3 presigned URLs)
- Document verification status

### ✅ Summary Statistics
- Completion percentage
- Document counts (total, verified, missing)
- User counts
- Submission eligibility

### ✅ Security & Authorization
- Role-based access control
- Firm association validation
- Admin override capabilities

### ✅ Performance Optimized
- Single query for complete data
- Efficient database joins
- Cached document type lookups