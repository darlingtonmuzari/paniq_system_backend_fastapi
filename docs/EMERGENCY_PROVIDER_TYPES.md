# Emergency Provider Types System

The Emergency Provider Types system allows administrators to manage and configure different types of emergency service providers. This system provides a centralized way to define provider categories with their specific characteristics, requirements, and display settings.

## Features

- **Type Management**: Create, read, update, and delete provider types
- **Validation**: Ensure emergency providers reference valid, active provider types
- **Configuration**: Set default coverage radius, license requirements, and priority levels
- **UI Support**: Define icons and colors for consistent user interface display
- **Role-Based Access**: Admin-only CRUD operations with read access for all users

## Provider Type Properties

Each provider type includes:

- **Basic Information**: Name, code, and description
- **Requirements**: License requirements and default coverage radius
- **Display Settings**: Icon identifier and color code for UI
- **Priority Level**: Operational priority (low, medium, high, critical)
- **Status**: Active/inactive flag for availability control

## Default Provider Types

The system comes with pre-configured provider types:

| Type | Code | Priority | License Required | Default Radius |
|------|------|----------|------------------|----------------|
| Ambulance | `ambulance` | Critical | Yes | 30 km |
| Fire Department | `fire_department` | Critical | Yes | 25 km |
| Police | `police` | High | Yes | 40 km |
| Medical | `medical` | High | Yes | 30 km |
| Tow Truck | `tow_truck` | Medium | Yes | 50 km |
| Security | `security` | Medium | No | 35 km |
| Roadside Assistance | `roadside_assistance` | Low | No | 60 km |

## API Endpoints

### Authentication & Authorization

**CRUD Operations** (Create, Update, Delete):
- `admin` - System administrators
- `super_admin` - Super administrators

**Read Operations** (List, Get):
- All authenticated users

### Provider Type Management

#### Create Provider Type
```http
POST /api/v1/emergency-provider-types
```

**Permissions:** `admin`, `super_admin`

**Request Body:**
```json
{
  "name": "Custom Emergency Service",
  "code": "custom_emergency",
  "description": "Custom emergency service provider type",
  "requires_license": true,
  "default_coverage_radius_km": 40.0,
  "icon": "custom-icon",
  "color": "#FF6600",
  "priority_level": "high"
}
```

**Response:**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "name": "Custom Emergency Service",
  "code": "custom_emergency",
  "description": "Custom emergency service provider type",
  "is_active": true,
  "requires_license": true,
  "default_coverage_radius_km": 40.0,
  "icon": "custom-icon",
  "color": "#FF6600",
  "priority_level": "high",
  "created_at": "2025-01-08T12:00:00Z",
  "updated_at": "2025-01-08T12:00:00Z"
}
```

#### List Provider Types
```http
GET /api/v1/emergency-provider-types
```

**Permissions:** All authenticated users

**Query Parameters:**
- `skip` - Number of records to skip (default: 0)
- `limit` - Maximum records to return (default: 100)
- `is_active` - Filter by active status (optional)

**Response:**
```json
[
  {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "name": "Ambulance",
    "code": "ambulance",
    "description": "Medical emergency services and patient transport",
    "is_active": true,
    "requires_license": true,
    "default_coverage_radius_km": 30.0,
    "icon": "ambulance",
    "color": "#FF4444",
    "priority_level": "critical",
    "created_at": "2025-01-08T12:00:00Z",
    "updated_at": "2025-01-08T12:00:00Z"
  }
]
```

#### Get Provider Type
```http
GET /api/v1/emergency-provider-types/{type_id}
```

**Permissions:** All authenticated users

#### Update Provider Type
```http
PUT /api/v1/emergency-provider-types/{type_id}
```

**Permissions:** `admin`, `super_admin`

**Request Body:**
```json
{
  "description": "Updated description",
  "default_coverage_radius_km": 45.0,
  "priority_level": "critical"
}
```

#### Delete Provider Type
```http
DELETE /api/v1/emergency-provider-types/{type_id}
```

**Permissions:** `admin`, `super_admin`

**Note:** Cannot delete provider types that are in use by existing emergency providers.

## Integration with Emergency Providers

### Foreign Key Relationship

Emergency providers now reference provider types through a foreign key relationship:

```json
{
  "name": "City Ambulance #1",
  "provider_type": "ambulance",
  "provider_type_id": "123e4567-e89b-12d3-a456-426614174000",
  "contact_phone": "+27123456789"
}
```

### Validation

When creating or updating emergency providers:

1. **Provider Type Validation**: The `provider_type_id` must reference an existing provider type
2. **Active Status Check**: The referenced provider type must be active
3. **License Validation**: If the provider type requires a license, the provider should include license information

### Migration

The system includes a database migration that:

1. Creates the `emergency_provider_types` table
2. Populates it with default provider types
3. Adds `provider_type_id` foreign key to `emergency_providers` table
4. Maps existing enum values to the new foreign key relationships

## Usage Examples

### Python Client Example

```python
import requests

# List all provider types
response = requests.get(
    "http://localhost:8000/api/v1/emergency-provider-types",
    headers={"Authorization": "Bearer your-jwt-token"}
)
provider_types = response.json()

# Create emergency provider with type validation
provider_data = {
    "name": "Metro Ambulance Service",
    "provider_type": "ambulance",
    "provider_type_id": "ambulance-type-uuid-here",
    "contact_phone": "+27123456789",
    "street_address": "123 Main St",
    "city": "Cape Town",
    "province": "Western Cape",
    "postal_code": "8001",
    "current_latitude": -33.9249,
    "current_longitude": 18.4241,
    "base_latitude": -33.9249,
    "base_longitude": 18.4241
}

response = requests.post(
    "http://localhost:8000/api/v1/emergency-providers",
    json=provider_data,
    headers={"Authorization": "Bearer your-jwt-token"}
)
```

### JavaScript Client Example

```javascript
// Get active provider types for dropdown
const getProviderTypes = async () => {
  const response = await fetch('/api/v1/emergency-provider-types?is_active=true', {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  return response.json();
};

// Create provider with type validation
const createProvider = async (providerData) => {
  const response = await fetch('/api/v1/emergency-providers', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify(providerData)
  });
  return response.json();
};
```

## Security Considerations

- **Admin-Only Management**: Only administrators can create, update, or delete provider types
- **Referential Integrity**: Provider types in use cannot be deleted
- **Validation**: All provider type references are validated before creating/updating providers
- **Audit Trail**: All operations are logged for security and compliance

## Best Practices

1. **Naming Convention**: Use descriptive names and consistent code formats
2. **Color Coding**: Use distinct colors for different priority levels
3. **Coverage Radius**: Set realistic default coverage areas based on service type
4. **License Requirements**: Accurately reflect legal requirements for each service type
5. **Priority Levels**: Align priority levels with emergency response protocols