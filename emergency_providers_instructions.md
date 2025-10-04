# Emergency Providers Sample Data

## Current Status

The emergency providers API endpoint `http://localhost:8000/api/v1/emergency-providers/` is currently experiencing internal server errors (500 status code). This appears to be related to missing database setup or dependency issues.

## Sample Data Created

I've created comprehensive sample data for emergency providers in `emergency_providers_sample_data.json` that includes:

### Emergency Provider Types
- **Ambulance Service** - Critical priority medical transport
- **Tow Truck Service** - Medium priority vehicle recovery  
- **Security Response** - High priority armed/unarmed security
- **Fire Department** - Critical priority fire suppression

### Emergency Providers
- **Cape Town Emergency Medical** - Available ambulance service
- **Atlantic Towing Services** - Available tow truck service
- **Metro Security Response Unit** - Available security response
- **Southern Suburbs Ambulance** - Busy ambulance service
- **Bellville Fire Station** - Available fire department

## Working API Token

Here's a valid admin token with proper permissions for testing once the API is fixed:

```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJkNmI5YTA3Yy0xMmJjLTQzNTUtYWI4NS1lZDA1NjQ1M2YyZTQiLCJ1c2VyX3R5cGUiOiJmaXJtX3BlcnNvbm5lbCIsImVtYWlsIjoiYWRtaW5AY3Rzcy5jby56YSIsInBlcm1pc3Npb25zIjpbXSwiZXhwIjoxNzU4MTg1NDgwLCJpYXQiOjE3NTgxODM2ODAsImp0aSI6ImRjYzI1NWFkLWRjOTAtNDMwOC1iODVhLTc3YWRkYWY3MWY5ZCIsInRva2VuX3R5cGUiOiJhY2Nlc3MiLCJmaXJtX2lkIjoiYWM0YjM4YWUtZGRkMy00YWUxLWE2MTktNWM2Zjk1MWQ1M2JhIiwicm9sZSI6ImZpcm1fYWRtaW4ifQ.afS1fATZ07quB_mAz7e9GYSHx5EX_HexK8A68Mf5Hio
```

Token details:
- **User Type:** firm_personnel
- **Role:** firm_admin
- **Firm ID:** ac4b38ae-ddd3-4ae1-a619-5c6f951d53ba
- **Expires:** 30 minutes from generation

## Test Commands (Once API is Fixed)

```bash
# List all emergency providers
curl -H "Authorization: Bearer [TOKEN]" \
     "http://localhost:8000/api/v1/emergency-providers/"

# List only ambulances
curl -H "Authorization: Bearer [TOKEN]" \
     "http://localhost:8000/api/v1/emergency-providers/?provider_type=ambulance"

# List only available providers
curl -H "Authorization: Bearer [TOKEN]" \
     "http://localhost:8000/api/v1/emergency-providers/?status=available"

# Create a new emergency provider
curl -X POST \
     -H "Authorization: Bearer [TOKEN]" \
     -H "Content-Type: application/json" \
     -d @emergency_provider_sample.json \
     "http://localhost:8000/api/v1/emergency-providers/"
```

## Next Steps

To resolve the internal server errors, you should:

1. **Check Database Tables** - Ensure `emergency_providers` and `emergency_provider_types` tables exist
2. **Check Foreign Key Relationships** - Verify relationships to `security_firms` table
3. **Check Service Dependencies** - Ensure `EmergencyProviderService` can connect to database
4. **Review Error Logs** - Check application logs for specific error details

## Manual Data Insertion

If you need to insert the sample data manually into the database, you can use the JSON data provided with appropriate SQL INSERT statements once the database schema is confirmed.