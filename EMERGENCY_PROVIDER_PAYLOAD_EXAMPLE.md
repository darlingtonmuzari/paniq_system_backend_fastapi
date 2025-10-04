# Emergency Provider API - Fixed Payload Example

## Issue Resolution

**Problem:** The API was requiring both `provider_type` (enum) and `provider_type_id` (UUID), but your payload only included `provider_type_id`.

**Solution:** Updated the API schema to make `provider_type` optional. The system now automatically derives the `provider_type` from the `provider_type_id` when not provided.

## Your Fixed Payload

Your original payload will now work without the `provider_type` field:

```json
{
  "name": "Emras",
  "provider_type_id": "3518e746-40d3-4a47-ac05-9b29d1a0a74f",
  "contact_phone": "+27746537701",
  "contact_email": "help@emars.com",
  "street_address": "100 Johannesburg Road",
  "city": "Lyndhurst",
  "province": "Gauteng",
  "country": "South Africa",
  "postal_code": "211",
  "description": "",
  "current_latitude": -26.1273,
  "current_longitude": 28.1128,
  "base_latitude": -26.1273,
  "base_longitude": 28.1128,
  "capabilities": ["basic_life_support", "emergency_medical_transport", "emergency_medical_services"],
  "status": "available",
  "equipment_details": "5 x AMC Ambulawances",
  "capacity": "5"
}
```

## What Happens Now

1. The API receives your payload with `provider_type_id: "3518e746-40d3-4a47-ac05-9b29d1a0a74f"`
2. It looks up this ID in the `emergency_provider_types` table
3. Finds: `name: "Ambulance", code: "ambulance"`
4. Automatically sets `provider_type: "ambulance"` (enum value)
5. Creates the emergency provider successfully

## Available Provider Type IDs

You can use any of these `provider_type_id` values:

| Provider Type ID | Name | Code |
|------------------|------|------|
| `3518e746-40d3-4a47-ac05-9b29d1a0a74f` | Ambulance | ambulance |
| `2c5360c5-d6de-490b-ab37-cd59e7eecc31` | Fire Department | fire_department |
| `a66e6f1c-4a46-4afb-a2a3-d8ddd5534b63` | Medical | medical |
| `80f2bcb0-fd31-4e2c-b0a1-7d8f041fa484` | Police | police |
| `6d44c983-f688-435e-9473-814ee0c3ccdd` | Roadside Assistance | roadside_assistance |
| `d3cfde69-cb37-4e6f-ad90-e0c5ae5db956` | Security | security |
| `d792cc4f-89a7-4fc2-b7fe-fa79aec347fe` | Tow Truck | tow_truck |

## Optional: Including provider_type

You can still optionally include the `provider_type` field if you want:

```json
{
  "name": "Emras",
  "provider_type": "ambulance",
  "provider_type_id": "3518e746-40d3-4a47-ac05-9b29d1a0a74f",
  // ... rest of payload
}
```

But it's no longer required - the system will derive it automatically.

## Complete cURL Example

```bash
curl -X POST "http://localhost:8000/api/v1/emergency-providers/" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Emras",
    "provider_type_id": "3518e746-40d3-4a47-ac05-9b29d1a0a74f",
    "contact_phone": "+27746537701",
    "contact_email": "help@emars.com",
    "street_address": "100 Johannesburg Road",
    "city": "Lyndhurst",
    "province": "Gauteng",
    "country": "South Africa",
    "postal_code": "211",
    "description": "",
    "current_latitude": -26.1273,
    "current_longitude": 28.1128,
    "base_latitude": -26.1273,
    "base_longitude": 28.1128,
    "capabilities": ["basic_life_support", "emergency_medical_transport", "emergency_medical_services"],
    "equipment_details": "5 x AMC Ambulances",
    "capacity": "5"
  }'
```

## Expected Response

```json
{
  "id": "uuid-here",
  "firm_id": "your-firm-id",
  "name": "Emras",
  "provider_type": "ambulance",
  "license_number": null,
  "contact_phone": "+27746537701",
  "contact_email": "help@emars.com",
  "current_latitude": -26.1273,
  "current_longitude": 28.1128,
  "base_latitude": -26.1273,
  "base_longitude": 28.1128,
  "coverage_radius_km": 50.0,
  "status": "available",
  "is_active": true,
  "description": "",
  "equipment_details": "5 x AMC Ambulances",
  "capacity": "5",
  "capabilities": ["basic_life_support", "emergency_medical_transport", "emergency_medical_services"],
  "created_at": "2025-09-19T08:56:35.601460+00:00",
  "updated_at": "2025-09-19T08:56:35.601460+00:00",
  "last_location_update": "2025-09-19T08:56:35.601460+00:00"
}
```

## Changes Made

1. **API Schema Updated**: `provider_type` field is now optional in `ProviderCreateRequest`
2. **Service Logic Enhanced**: Automatically derives `provider_type` from `provider_type_id` lookup
3. **Backward Compatibility**: Still accepts `provider_type` if provided
4. **Documentation Updated**: API docs now reflect the optional nature of `provider_type`

Your payload should now work perfectly without needing the `provider_type` field!