# Emergency Providers System

The Emergency Providers system allows security firms to register and manage their emergency service providers such as ambulances, tow trucks, fire departments, and other emergency services. The system includes distance calculation capabilities to find the nearest available providers for emergency requests.

## Features

- **Provider Registration**: Register various types of emergency providers
- **Location Tracking**: Track current and base locations of providers
- **Distance Calculation**: Calculate distances between providers and emergency locations
- **Availability Management**: Track provider status (available, busy, offline, maintenance)
- **Assignment System**: Assign providers to emergency requests
- **Coverage Areas**: Define coverage radius for each provider

## Provider Types

The system supports the following provider types:

- `ambulance` - Medical emergency services
- `tow_truck` - Vehicle towing and roadside assistance
- `fire_department` - Fire and rescue services
- `police` - Law enforcement services
- `security` - Private security services
- `medical` - General medical services
- `roadside_assistance` - Vehicle breakdown assistance

## Provider Status

Each provider can have one of the following statuses:

- `available` - Ready to respond to requests
- `busy` - Currently assigned to a request
- `offline` - Not available for assignments
- `maintenance` - Under maintenance or repair

## API Endpoints

### Provider Management

#### Create Provider
```http
POST /api/v1/emergency-providers
```

Creates a new emergency provider for the firm.

**Request Body:**
```json
{
  "name": "City Emergency Ambulance #1",
  "provider_type": "ambulance",
  "license_number": "AMB-001-2024",
  "contact_phone": "+27123456789",
  "contact_email": "ambulance1@cityemergency.co.za",
  "current_latitude": -26.2041,
  "current_longitude": 28.0473,
  "base_latitude": -26.2041,
  "base_longitude": 28.0473,
  "coverage_radius_km": 25.0,
  "description": "Advanced Life Support ambulance",
  "equipment_details": "{\"defibrillator\": true, \"oxygen\": true}",
  "capacity": "2 patients, 2 paramedics"
}
```

#### Get Firm Providers
```http
GET /api/v1/emergency-providers
```

Query parameters:
- `provider_type` - Filter by provider type
- `status` - Filter by status
- `include_inactive` - Include inactive providers

#### Get Provider by ID
```http
GET /api/v1/emergency-providers/{provider_id}
```

#### Update Provider
```http
PUT /api/v1/emergency-providers/{provider_id}
```

#### Update Provider Location
```http
PATCH /api/v1/emergency-providers/{provider_id}/location
```

**Request Body:**
```json
{
  "latitude": -26.2100,
  "longitude": 28.0500
}
```

#### Delete Provider
```http
DELETE /api/v1/emergency-providers/{provider_id}
```

#### Delete Unused Providers
```http
DELETE /api/v1/emergency-providers/cleanup/unused
```

Removes emergency providers that haven't been used in any emergency requests. This is useful for cleaning up test data or removing inactive providers.

**Permissions:** `firm_user`, `firm_supervisor`, `firm_admin`

**Response:**
```json
{
  "message": "Successfully deleted 5 unused emergency providers",
  "deleted_count": 5
}
```

**Note:** This operation is irreversible. Ensure you have backups if needed.

### Provider Search

#### Find Nearest Providers
```http
GET /api/v1/emergency-providers/search/nearest
```

Query parameters:
- `latitude` - Search location latitude
- `longitude` - Search location longitude
- `provider_type` - Type of provider to search for
- `max_distance_km` - Maximum search distance (default: 100km)
- `limit` - Maximum number of results (default: 10)

**Example:**
```http
GET /api/v1/emergency-providers/search/nearest?latitude=-26.2000&longitude=28.0400&provider_type=ambulance&max_distance_km=30&limit=5
```

**Response:**
```json
{
  "providers": [
    {
      "provider": {
        "id": "uuid",
        "name": "City Emergency Ambulance #1",
        "provider_type": "ambulance",
        "current_latitude": -26.2041,
        "current_longitude": 28.0473,
        "status": "available"
      },
      "distance_km": 2.5,
      "estimated_duration_minutes": 4.2
    }
  ],
  "search_location": {
    "latitude": -26.2000,
    "longitude": 28.0400
  },
  "max_distance_km": 30
}
```

### Provider Assignment

#### Assign Provider to Request
```http
POST /api/v1/emergency-providers/{provider_id}/assign
```

**Request Body:**
```json
{
  "request_id": "emergency-request-uuid",
  "estimated_arrival_time": "2024-01-08T14:30:00Z"
}
```

## Distance Calculation

The system uses the Haversine formula to calculate distances between geographical points:

```python
def calculate_distance(lat1, lon1, lat2, lon2):
    # Convert to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    # Earth radius in kilometers
    r = 6371
    
    return c * r
```

### Travel Time Estimation

The system estimates travel time based on distance and assumed average speeds:

- **City driving** (≤10km): 40 km/h average speed
- **Suburban** (10-50km): 60 km/h average speed  
- **Highway** (>50km): 80 km/h average speed

## Database Schema

### emergency_providers table

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| firm_id | UUID | Foreign key to security_firms |
| name | VARCHAR(255) | Provider name |
| provider_type | ENUM | Type of provider |
| license_number | VARCHAR(100) | License/registration number |
| contact_phone | VARCHAR(20) | Contact phone number |
| contact_email | VARCHAR(255) | Contact email |
| current_latitude | FLOAT | Current location latitude |
| current_longitude | FLOAT | Current location longitude |
| base_latitude | FLOAT | Base location latitude |
| base_longitude | FLOAT | Base location longitude |
| coverage_radius_km | FLOAT | Coverage radius in km |
| status | ENUM | Provider status |
| is_active | BOOLEAN | Whether provider is active |
| description | TEXT | Provider description |
| equipment_details | TEXT | Equipment details (JSON) |
| capacity | VARCHAR(100) | Capacity information |
| created_at | TIMESTAMP | Creation timestamp |
| updated_at | TIMESTAMP | Last update timestamp |
| last_location_update | TIMESTAMP | Last location update |

### provider_assignments table

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| provider_id | UUID | Foreign key to emergency_providers |
| request_id | UUID | Foreign key to panic_requests |
| assigned_at | TIMESTAMP | Assignment timestamp |
| estimated_arrival_time | TIMESTAMP | Estimated arrival time |
| actual_arrival_time | TIMESTAMP | Actual arrival time |
| completion_time | TIMESTAMP | Completion timestamp |
| distance_km | FLOAT | Distance to request location |
| estimated_duration_minutes | FLOAT | Estimated travel duration |
| status | VARCHAR(50) | Assignment status |
| notes | TEXT | Assignment notes |

## Usage Examples

### 1. Register an Ambulance Service

```python
import requests

# Create ambulance provider
ambulance_data = {
    "name": "City Emergency Ambulance #1",
    "provider_type": "ambulance",
    "license_number": "AMB-001-2024",
    "contact_phone": "+27123456789",
    "current_latitude": -26.2041,
    "current_longitude": 28.0473,
    "base_latitude": -26.2041,
    "base_longitude": 28.0473,
    "coverage_radius_km": 25.0,
    "description": "Advanced Life Support ambulance",
    "capacity": "2 patients, 2 paramedics"
}

response = requests.post(
    "http://localhost:8000/api/v1/emergency-providers",
    json=ambulance_data,
    headers={"Authorization": "Bearer your-jwt-token"}
)
```

### 2. Find Nearest Ambulance

```python
# Search for nearest ambulances
params = {
    "latitude": -26.2000,
    "longitude": 28.0400,
    "provider_type": "ambulance",
    "max_distance_km": 30,
    "limit": 5
}

response = requests.get(
    "http://localhost:8000/api/v1/emergency-providers/search/nearest",
    params=params,
    headers={"Authorization": "Bearer your-jwt-token"}
)

nearest_providers = response.json()["providers"]
```

### 3. Update Provider Location

```python
# Update ambulance location
location_data = {
    "latitude": -26.2100,
    "longitude": 28.0500
}

response = requests.patch(
    f"http://localhost:8000/api/v1/emergency-providers/{provider_id}/location",
    json=location_data,
    headers={"Authorization": "Bearer your-jwt-token"}
)
```

## Security & Authorization

### Role-Based Access Control

**CRUD Operations** (Create, Update, Delete):
- `firm_user` - Basic firm personnel
- `firm_supervisor` - Supervisory firm personnel  
- `firm_admin` - Firm administrators

**Read Operations** (List, Get, Search):
- `firm_user`, `firm_supervisor`, `firm_admin` - Firm personnel
- `team_leader`, `field_agent` - Field personnel
- `admin`, `super_admin` - System administrators

### Additional Security Features
- Firms can only manage their own providers
- Provider assignments are tracked for audit purposes
- All operations require valid JWT authentication
- Location updates are timestamped for tracking

## Integration with Emergency Requests

The emergency providers system integrates with the existing emergency request system:

1. When an emergency request is created, the system can automatically search for nearest available providers
2. Providers can be assigned to requests with distance and time calculations
3. Assignment status is tracked throughout the emergency response process
4. Performance metrics are collected for response time analysis

## Future Enhancements

- **Real-time GPS tracking** integration
- **Route optimization** using mapping services
- **Automatic assignment** based on proximity and availability
- **Performance analytics** and reporting
- **Mobile app** for provider status updates
- **Integration with external services** (Google Maps, traffic data)