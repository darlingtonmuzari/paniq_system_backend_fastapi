# Location Tracking System

## Overview

The Location Tracking System provides real-time location monitoring for panic requests, allowing users to continuously update their location during an emergency. This system creates a detailed location history while also updating the main panic request location as needed.

## Features

- **Continuous Location Logging**: Track user location changes throughout a panic request
- **Location History**: Maintain a complete timeline of user movements
- **Multiple Sources**: Support location updates from mobile, web, and manual sources
- **GPS Accuracy Tracking**: Record GPS accuracy for each location update
- **Distance Calculation**: Calculate total distance traveled during an emergency
- **Real-time Updates**: Update the main panic request location simultaneously

## Database Schema

### location_logs Table

```sql
CREATE TABLE location_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id UUID NOT NULL REFERENCES panic_requests(id),
    user_id UUID NOT NULL REFERENCES registered_users(id),
    location GEOMETRY(POINT, 4326) NOT NULL,
    address TEXT,
    accuracy INTEGER,  -- GPS accuracy in meters
    source VARCHAR(20) NOT NULL DEFAULT 'mobile',  -- mobile, web, manual
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

-- Indexes for performance
CREATE INDEX idx_location_logs_request_id ON location_logs(request_id);
CREATE INDEX idx_location_logs_user_id ON location_logs(user_id);
CREATE INDEX idx_location_logs_location ON location_logs USING GIST(location);
CREATE INDEX idx_location_logs_created_at ON location_logs(created_at);
```

### Relationship with panic_requests

The `panic_requests` table has a `location_logs` relationship:
```python
location_logs = relationship("LocationLog", cascade="all, delete-orphan")
```

## API Endpoints

### POST /api/v1/location-tracking/update

Update user location during a panic request.

**Request Body:**
```json
{
  "request_id": "uuid",
  "latitude": 40.7128,
  "longitude": -74.0060,
  "address": "123 Main St, New York, NY",
  "accuracy": 5,
  "source": "mobile",
  "update_panic_request": true
}
```

**Response:**
```json
{
  "id": "uuid",
  "request_id": "uuid",
  "user_id": "uuid",
  "latitude": 40.7128,
  "longitude": -74.0060,
  "address": "123 Main St, New York, NY",
  "accuracy": 5,
  "source": "mobile",
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:30:00Z"
}
```

### GET /api/v1/location-tracking/request/{request_id}

Get location history for a specific panic request.

**Parameters:**
- `limit`: Maximum number of logs to return (default: 100)

**Response:**
```json
{
  "logs": [...],
  "total_count": 25
}
```

### GET /api/v1/location-tracking/request/{request_id}/latest

Get the most recent location for a panic request.

**Response:**
```json
{
  "id": "uuid",
  "request_id": "uuid",
  "user_id": "uuid",
  "latitude": 40.7128,
  "longitude": -74.0060,
  "address": "123 Main St, New York, NY",
  "accuracy": 5,
  "source": "mobile",
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:30:00Z"
}
```

### GET /api/v1/location-tracking/request/{request_id}/distance

Calculate total distance traveled during a panic request.

**Parameters:**
- `from_time`: Start time for calculation (ISO 8601 format)
- `to_time`: End time for calculation (optional, defaults to now)

**Response:**
```json
{
  "request_id": "uuid",
  "distance_meters": 1250.5,
  "from_time": "2025-01-15T10:00:00Z",
  "to_time": "2025-01-15T10:30:00Z"
}
```

## Service Layer

### LocationLogService

The `LocationLogService` class handles all location tracking operations:

#### Key Methods:

- `create_location_log()`: Create a new location log entry
- `get_location_logs_for_request()`: Get all location logs for a request
- `get_latest_location_for_request()`: Get the most recent location
- `update_panic_request_location()`: Update the main panic request location
- `extract_coordinates()`: Extract lat/lng from geometry
- `get_location_distance()`: Calculate distance traveled

## Usage Examples

### Mobile App Integration

```javascript
// Update location every 30 seconds during a panic request
const updateLocation = async (requestId, position) => {
  const locationData = {
    request_id: requestId,
    latitude: position.coords.latitude,
    longitude: position.coords.longitude,
    accuracy: position.coords.accuracy,
    source: 'mobile',
    update_panic_request: true
  };
  
  const response = await fetch('/api/v1/location-tracking/update', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${accessToken}`
    },
    body: JSON.stringify(locationData)
  });
  
  return response.json();
};

// Get location updates every 30 seconds
navigator.geolocation.watchPosition(
  (position) => updateLocation(currentRequestId, position),
  (error) => console.error('Location error:', error),
  { enableHighAccuracy: true, timeout: 5000, maximumAge: 10000 }
);
```

### Emergency Response Dashboard

```javascript
// Get live location updates for emergency responders
const getLocationHistory = async (requestId) => {
  const response = await fetch(`/api/v1/location-tracking/request/${requestId}`);
  const data = await response.json();
  
  // Display on map
  data.logs.forEach(log => {
    addMarkerToMap(log.latitude, log.longitude, {
      timestamp: log.created_at,
      accuracy: log.accuracy,
      source: log.source
    });
  });
};

// Get current location
const getCurrentLocation = async (requestId) => {
  const response = await fetch(`/api/v1/location-tracking/request/${requestId}/latest`);
  const location = await response.json();
  
  // Update emergency responder with latest position
  updateResponderMap(location.latitude, location.longitude);
};
```

## Security Considerations

### Authentication
- All endpoints require user authentication via JWT token
- Users can only access location data for their own requests
- Emergency responders can access location data for assigned requests

### Privacy
- Location data is only stored during active panic requests
- Historical location data can be purged based on retention policies
- GPS accuracy is recorded to assess data reliability

### Data Protection
- All location coordinates are stored using PostGIS GEOMETRY type
- Spatial indexes are used for efficient location-based queries
- Location data is encrypted at rest

## Performance Optimization

### Database Indexes
- GIST index on location column for spatial queries
- B-tree indexes on request_id and user_id for fast lookups
- Composite indexes for time-range queries

### Caching Strategy
- Latest location per request cached in Redis
- Location history cached for active requests
- Cache invalidation on new location updates

### Query Optimization
- Use spatial functions for distance calculations
- Limit historical queries to reasonable time windows
- Batch location updates where possible

## Monitoring and Alerts

### Metrics to Track
- Location update frequency per request
- GPS accuracy trends
- Distance traveled during emergencies
- Response time for location queries

### Alerts
- Missing location updates for active requests
- Unusual movement patterns (potential false alarms)
- GPS accuracy below acceptable thresholds
- High frequency of location updates (potential spam)

## Future Enhancements

### Planned Features
- **Geofencing**: Alert when user moves outside expected area
- **Route Optimization**: Suggest optimal routes for emergency responders
- **Location Sharing**: Share live location with trusted contacts
- **Offline Caching**: Store locations locally when connectivity is poor
- **Location Verification**: Cross-reference with cell tower data

### Integration Opportunities
- **Google Maps Integration**: Enhanced mapping and geocoding
- **Emergency Services**: Direct integration with 911/emergency dispatch
- **IoT Devices**: Support for wearable devices and vehicle trackers
- **Machine Learning**: Predict movement patterns and optimize response

## Troubleshooting

### Common Issues

#### Location Not Updating
- Check user permissions for location access
- Verify GPS signal strength
- Confirm panic request is still active
- Check network connectivity

#### Inaccurate Locations
- Review GPS accuracy values in logs
- Consider environmental factors (indoor, urban canyons)
- Check for device-specific GPS issues
- Validate coordinate system (should be WGS84/EPSG:4326)

#### Performance Issues
- Review database query performance
- Check spatial index usage
- Monitor location update frequency
- Consider caching strategies

### Debugging Tools

#### SQL Queries
```sql
-- Get location history for a request
SELECT 
    id, 
    ST_X(location) as longitude,
    ST_Y(location) as latitude,
    accuracy,
    source,
    created_at
FROM location_logs 
WHERE request_id = 'your-request-id'
ORDER BY created_at DESC;

-- Calculate distance between consecutive points
SELECT 
    ST_Distance(
        lag(location) OVER (ORDER BY created_at),
        location
    ) as distance_meters
FROM location_logs 
WHERE request_id = 'your-request-id'
ORDER BY created_at;
```

#### API Testing
```bash
# Test location update
curl -X POST "http://localhost:8000/api/v1/location-tracking/update" \
  -H "Authorization: Bearer your-token" \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "uuid",
    "latitude": 40.7128,
    "longitude": -74.0060,
    "source": "mobile"
  }'

# Get location history
curl -X GET "http://localhost:8000/api/v1/location-tracking/request/uuid" \
  -H "Authorization: Bearer your-token"
```

## Implementation Status

- ✅ Database schema created
- ✅ Location logs model implemented
- ✅ Service layer completed
- ✅ API endpoints functional
- ✅ Authentication integrated
- ✅ Basic documentation complete
- ⏳ Frontend integration pending
- ⏳ Real-time WebSocket updates pending
- ⏳ Advanced monitoring pending