# Emergency Providers API Documentation

## Overview

The Emergency Providers API manages emergency service providers (ambulances, tow trucks, fire departments, etc.) for security firms. This API allows firms to register, update, track, and manage their emergency service vehicles and personnel.

**Base URL:** `http://localhost:8000/api/v1/emergency-providers`

**Authentication:** Bearer token required for all endpoints

**Permissions:**
- **Read Access:** `require_emergency_provider_read` - All firm personnel
- **CRUD Access:** `require_emergency_provider_crud` - Firm supervisors and admins only

---

## Data Models & Enums

### Provider Types (`ProviderType`)
```typescript
enum ProviderType {
  AMBULANCE = "ambulance",
  TOW_TRUCK = "tow_truck", 
  FIRE_DEPARTMENT = "fire_department",
  POLICE = "police",
  SECURITY = "security",
  MEDICAL = "medical",
  ROADSIDE_ASSISTANCE = "roadside_assistance"
}
```

### Provider Status (`ProviderStatus`)
```typescript
enum ProviderStatus {
  AVAILABLE = "available",
  BUSY = "busy",
  OFFLINE = "offline", 
  MAINTENANCE = "maintenance"
}
```

---

## API Endpoints

### 1. Create Emergency Provider

**`POST /`**

Creates a new emergency provider for the authenticated firm.

#### Request Body (`ProviderCreateRequest`)

```json
{
  "name": "string",                    // Required, 1-255 chars
  "provider_type": "ProviderType",     // Optional, will be derived from provider_type_id if not provided
  "provider_type_id": "string",        // Required, UUID of provider type
  "license_number": "string",          // Optional, max 100 chars
  "contact_phone": "string",           // Required, 10-20 chars
  "contact_email": "string",           // Optional, max 255 chars
  
  // Address Information (accepted but not stored in current version)
  "street_address": "string",          // Required, 1-500 chars
  "city": "string",                    // Required, 1-100 chars
  "province": "string",                // Required, 1-100 chars
  "country": "string",                 // Optional, default "South Africa", 1-100 chars
  "postal_code": "string",             // Required, 1-20 chars
  
  // Location Information (GPS coordinates)
  "current_latitude": "number",        // Required, -90 to 90
  "current_longitude": "number",       // Required, -180 to 180
  "base_latitude": "number",           // Required, -90 to 90
  "base_longitude": "number",          // Required, -180 to 180
  "coverage_radius_km": "number",      // Optional, default 50.0, max 500
  
  // Additional Details
  "description": "string",             // Optional, max 1000 chars
  "equipment_details": "string",       // Optional, max 2000 chars, JSON format
  "capacity": "string",                // Optional, max 100 chars
  "capabilities": ["string"]           // Optional, array of capability codes
}
```

#### Example Request
```json
{
  "name": "Metro Ambulance Unit 1",
  "provider_type_id": "550e8400-e29b-41d4-a716-446655440001",
  "license_number": "AMB-001-2024",
  "contact_phone": "+27123456789",
  "contact_email": "unit1@metro-medical.co.za",
  "street_address": "123 Hospital Road",
  "city": "Cape Town",
  "province": "Western Cape",
  "country": "South Africa",
  "postal_code": "8001",
  "current_latitude": -33.9249,
  "current_longitude": 18.4241,
  "base_latitude": -33.9249,
  "base_longitude": 18.4241,
  "coverage_radius_km": 75.0,
  "description": "Advanced life support ambulance",
  "equipment_details": "{\"defibrillator\": true, \"ventilator\": true, \"stretchers\": 2}",
  "capacity": "2 patients",
  "capabilities": ["advanced_life_support", "cardiac_care", "emergency_medical_transport"]
}
```

#### Response (`ProviderResponse`)
```json
{
  "id": "string",                      // UUID
  "firm_id": "string",                 // UUID
  "name": "string",
  "provider_type": "string",           // ProviderType value
  "license_number": "string",
  "contact_phone": "string",
  "contact_email": "string",
  "current_latitude": "number",
  "current_longitude": "number", 
  "base_latitude": "number",
  "base_longitude": "number",
  "coverage_radius_km": "number",
  "status": "string",                  // ProviderStatus value
  "is_active": "boolean",
  "description": "string",
  "equipment_details": "string",
  "capacity": "string",
  "capabilities": ["string"],
  "created_at": "string",              // ISO 8601 datetime
  "updated_at": "string",              // ISO 8601 datetime
  "last_location_update": "string"     // ISO 8601 datetime
}
```

#### HTTP Status Codes
- `200` - Provider created successfully
- `400` - Invalid request data or validation error
- `401` - Authentication required
- `403` - Insufficient permissions
- `500` - Internal server error

---

### 2. Get Firm's Emergency Providers

**`GET /`**

Retrieves all emergency providers for the authenticated firm with optional filtering.

#### Query Parameters
```typescript
{
  provider_type?: ProviderType,        // Optional, filter by provider type
  provider_status?: ProviderStatus,    // Optional, filter by status
  include_inactive?: boolean           // Optional, default false
}
```

#### Example Request
```
GET /api/v1/emergency-providers/?provider_type=ambulance&provider_status=available&include_inactive=true
```

#### Response (`ProviderListResponse`)
```json
{
  "providers": [
    {
      // ProviderResponse objects (see above)
    }
  ],
  "total_count": "number"
}
```

#### HTTP Status Codes
- `200` - Success
- `401` - Authentication required
- `403` - Insufficient permissions
- `500` - Internal server error

---

### 3. Get Emergency Provider by ID

**`GET /{provider_id}`**

Retrieves detailed information about a specific emergency provider.

#### Path Parameters
- `provider_id`: UUID of the emergency provider

#### Response (`ProviderResponse`)
Same as create provider response.

#### HTTP Status Codes
- `200` - Success
- `400` - Invalid provider ID format
- `401` - Authentication required
- `403` - Provider belongs to different firm
- `404` - Provider not found
- `500` - Internal server error

---

### 4. Update Emergency Provider

**`PUT /{provider_id}`**

Updates an existing emergency provider. Only non-null fields are updated.

#### Path Parameters
- `provider_id`: UUID of the emergency provider

#### Request Body (`ProviderUpdateRequest`)
```json
{
  // All fields optional - only provided fields will be updated
  "name": "string",
  "provider_type_id": "string",
  "contact_phone": "string", 
  "contact_email": "string",
  "street_address": "string",
  "city": "string",
  "province": "string",
  "country": "string",
  "postal_code": "string",
  "current_latitude": "number",
  "current_longitude": "number",
  "base_latitude": "number", 
  "base_longitude": "number",
  "coverage_radius_km": "number",
  "status": "ProviderStatus",
  "description": "string",
  "equipment_details": "string",
  "capacity": "string",
  "capabilities": ["string"],
  "is_active": "boolean"
}
```

#### Example Request
```json
{
  "status": "busy",
  "current_latitude": -33.9355,
  "current_longitude": 18.4483,
  "equipment_details": "{\"defibrillator\": true, \"ventilator\": true, \"stretchers\": 2, \"oxygen_tank\": \"full\"}"
}
```

#### Response (`ProviderResponse`)
Returns the updated provider object.

#### HTTP Status Codes
- `200` - Updated successfully
- `400` - Invalid request data
- `401` - Authentication required
- `403` - Provider belongs to different firm
- `404` - Provider not found
- `500` - Internal server error

---

### 5. Update Provider Location

**`PATCH /{provider_id}/location`**

Updates only the current location of a provider. Used for real-time location tracking.

#### Path Parameters
- `provider_id`: UUID of the emergency provider

#### Request Body (`LocationUpdateRequest`)
```json
{
  "latitude": "number",               // Required, -90 to 90
  "longitude": "number"               // Required, -180 to 180
}
```

#### Example Request
```json
{
  "latitude": -33.9355,
  "longitude": 18.4483
}
```

#### Response (`ProviderResponse`)
Returns the updated provider object with new location and updated `last_location_update` timestamp.

#### HTTP Status Codes
- `200` - Location updated successfully
- `400` - Invalid coordinates
- `401` - Authentication required
- `403` - Provider belongs to different firm
- `404` - Provider not found
- `500` - Internal server error

---

### 6. Delete Emergency Provider

**`DELETE /{provider_id}`**

Deactivates an emergency provider. Providers with active assignments cannot be deleted.

#### Path Parameters
- `provider_id`: UUID of the emergency provider

#### Response
```json
{
  "message": "Emergency provider deleted successfully"
}
```

#### HTTP Status Codes
- `200` - Deleted successfully
- `400` - Provider has active assignments or other constraints
- `401` - Authentication required
- `403` - Provider belongs to different firm
- `404` - Provider not found
- `500` - Internal server error

---

### 7. Find Nearest Providers

**`GET /search/nearest`**

Searches for the nearest available emergency providers of a specific type within a maximum distance.

#### Query Parameters
```typescript
{
  latitude: number,                   // Required, -90 to 90
  longitude: number,                  // Required, -180 to 180
  provider_type: ProviderType,        // Required
  max_distance_km?: number,           // Optional, default 100.0, max 500
  limit?: number                      // Optional, default 10, max 50
}
```

#### Example Request
```
GET /api/v1/emergency-providers/search/nearest?latitude=-33.9249&longitude=18.4241&provider_type=ambulance&max_distance_km=50&limit=5
```

#### Response (`NearestProvidersResponse`)
```json
{
  "providers": [
    {
      "provider": {
        // ProviderResponse object
      },
      "distance_km": "number",
      "estimated_duration_minutes": "number"
    }
  ],
  "search_location": {
    "latitude": "number",
    "longitude": "number"
  },
  "max_distance_km": "number"
}
```

#### HTTP Status Codes
- `200` - Search completed successfully
- `400` - Invalid search parameters
- `401` - Authentication required
- `403` - Insufficient permissions
- `500` - Internal server error

---

### 8. Assign Provider to Emergency Request

**`POST /{provider_id}/assign`**

Assigns a provider to an emergency request. The provider must be available and belong to the firm.

#### Path Parameters
- `provider_id`: UUID of the emergency provider

#### Request Body (`AssignmentRequest`)
```json
{
  "request_id": "string",                    // Required, UUID of emergency request
  "estimated_arrival_time": "string"        // Optional, ISO 8601 datetime
}
```

#### Example Request
```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440002",
  "estimated_arrival_time": "2024-01-15T14:30:00Z"
}
```

#### Response (`AssignmentResponse`)
```json
{
  "id": "string",                           // Assignment UUID
  "provider_id": "string",                  // Provider UUID
  "request_id": "string",                   // Request UUID
  "assigned_at": "string",                  // ISO 8601 datetime
  "estimated_arrival_time": "string",       // ISO 8601 datetime
  "distance_km": "number",
  "estimated_duration_minutes": "number",
  "status": "string"
}
```

#### HTTP Status Codes
- `200` - Assignment created successfully
- `400` - Invalid request or provider not available
- `401` - Authentication required
- `403` - Provider belongs to different firm
- `404` - Provider not found
- `500` - Internal server error

---

### 9. Delete Unused Providers

**`DELETE /cleanup/unused`**

Deletes emergency providers that haven't been used in any emergency requests. Bulk cleanup operation.

#### Response
```json
{
  "message": "Successfully deleted {count} unused emergency providers",
  "deleted_count": "number"
}
```

#### HTTP Status Codes
- `200` - Cleanup completed successfully
- `401` - Authentication required
- `403` - Insufficient permissions
- `500` - Internal server error

---

## Common Response Fields

### Error Response Format
```json
{
  "error_code": "string",               // HTTP error code
  "message": "string",                  // Human-readable error message
  "details": {},                        // Additional error details
  "timestamp": "string",                // ISO 8601 datetime
  "request_id": "string"                // Optional request tracking ID
}
```

### Timestamp Format
All timestamps are in ISO 8601 format with timezone: `"2024-01-15T14:30:00.123456+00:00"`

### UUID Format
All UUIDs are in standard format: `"550e8400-e29b-41d4-a716-446655440000"`

---

## Usage Examples

### Complete Provider Registration Flow

1. **Create a new ambulance:**
```bash
curl -X POST "http://localhost:8000/api/v1/emergency-providers/" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Metro Ambulance Unit 1",
    "provider_type": "ambulance",
    "provider_type_id": "550e8400-e29b-41d4-a716-446655440001",
    "contact_phone": "+27123456789",
    "street_address": "123 Hospital Road",
    "city": "Cape Town",
    "province": "Western Cape",
    "postal_code": "8001",
    "current_latitude": -33.9249,
    "current_longitude": 18.4241,
    "base_latitude": -33.9249,
    "base_longitude": 18.4241,
    "coverage_radius_km": 75.0
  }'
```

2. **Update provider location in real-time:**
```bash
curl -X PATCH "http://localhost:8000/api/v1/emergency-providers/{provider_id}/location" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "latitude": -33.9355,
    "longitude": 18.4483
  }'
```

3. **Find nearest available ambulances:**
```bash
curl "http://localhost:8000/api/v1/emergency-providers/search/nearest?latitude=-33.9249&longitude=18.4241&provider_type=ambulance&max_distance_km=50" \
  -H "Authorization: Bearer {token}"
```

4. **Assign provider to emergency:**
```bash
curl -X POST "http://localhost:8000/api/v1/emergency-providers/{provider_id}/assign" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "550e8400-e29b-41d4-a716-446655440002"
  }'
```

---

## Best Practices

1. **Location Updates**: Use the PATCH location endpoint for frequent location updates rather than full PUT updates
2. **Search Optimization**: Use appropriate `max_distance_km` and `limit` values to optimize search performance
3. **Status Management**: Keep provider status updated (available/busy/offline) for accurate dispatching
4. **Capability Tracking**: Maintain accurate capability arrays for proper provider matching
5. **Error Handling**: Always check response status codes and handle errors gracefully
6. **Authentication**: Ensure Bearer tokens are valid and have appropriate permissions

---

## Rate Limits

- **Location Updates**: Recommended maximum 1 update per 30 seconds per provider
- **Search Requests**: Maximum 60 requests per minute per firm
- **General API**: Maximum 1000 requests per hour per firm

---

## Security Considerations

- All endpoints require valid authentication
- Firms can only access their own providers
- Location data should be transmitted over HTTPS
- Provider assignments are tracked for audit purposes
- Sensitive equipment details should be properly formatted JSON