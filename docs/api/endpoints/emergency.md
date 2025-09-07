# Emergency Request API

The Emergency API handles panic request submission, processing, and coordination between users, security firms, and service providers.

## Endpoints

### POST /api/v1/emergency/request

Submit a panic request for emergency services.

**Headers:**
```
Authorization: Bearer YOUR_ACCESS_TOKEN
X-Attestation-Token: YOUR_ATTESTATION_TOKEN (mobile only)
X-Platform: android|ios (mobile only)
```

**Request Body:**
```json
{
  "service_type": "security",
  "location": {
    "latitude": 40.7128,
    "longitude": -74.0060
  },
  "address": "123 Main St, New York, NY",
  "description": "Suspicious activity outside my home",
  "group_id": "123e4567-e89b-12d3-a456-426614174000"
}
```

**Service Types:**
- `call` - Phone call service (sets phone to silent mode)
- `security` - Security personnel dispatch
- `ambulance` - Medical emergency
- `fire` - Fire emergency
- `towing` - Vehicle towing service

**Response:**
```json
{
  "request_id": "req_123456789",
  "status": "pending",
  "estimated_response_time": 15,
  "assigned_team": null,
  "created_at": "2024-08-24T10:30:00Z"
}
```

### GET /api/v1/emergency/requests

Get user's emergency request history.

**Headers:**
```
Authorization: Bearer YOUR_ACCESS_TOKEN
```

**Query Parameters:**
- `status` (optional): Filter by status (pending, assigned, in_progress, completed)
- `service_type` (optional): Filter by service type
- `limit` (optional): Number of results (default: 20, max: 100)
- `offset` (optional): Pagination offset

**Response:**
```json
{
  "requests": [
    {
      "request_id": "req_123456789",
      "service_type": "security",
      "status": "completed",
      "location": {
        "latitude": 40.7128,
        "longitude": -74.0060
      },
      "address": "123 Main St, New York, NY",
      "created_at": "2024-08-24T10:30:00Z",
      "completed_at": "2024-08-24T11:00:00Z",
      "response_time_minutes": 30
    }
  ],
  "total": 1,
  "has_more": false
}
```
###
 GET /api/v1/emergency/requests/{request_id}

Get details of a specific emergency request.

**Headers:**
```
Authorization: Bearer YOUR_ACCESS_TOKEN
```

**Response:**
```json
{
  "request_id": "req_123456789",
  "service_type": "security",
  "status": "in_progress",
  "location": {
    "latitude": 40.7128,
    "longitude": -74.0060
  },
  "address": "123 Main St, New York, NY",
  "description": "Suspicious activity outside my home",
  "assigned_team": {
    "team_id": "team_456",
    "team_name": "Alpha Team",
    "agent_name": "John Smith",
    "agent_phone": "+1234567890",
    "estimated_arrival": "2024-08-24T10:45:00Z"
  },
  "timeline": [
    {
      "status": "pending",
      "timestamp": "2024-08-24T10:30:00Z",
      "message": "Request submitted"
    },
    {
      "status": "assigned",
      "timestamp": "2024-08-24T10:32:00Z",
      "message": "Assigned to Alpha Team"
    },
    {
      "status": "in_progress",
      "timestamp": "2024-08-24T10:35:00Z",
      "message": "Agent en route"
    }
  ],
  "created_at": "2024-08-24T10:30:00Z"
}
```

### PUT /api/v1/emergency/requests/{request_id}/status

Update request status (for field agents and office staff).

**Headers:**
```
Authorization: Bearer YOUR_ACCESS_TOKEN
X-Attestation-Token: YOUR_ATTESTATION_TOKEN (mobile only)
```

**Request Body:**
```json
{
  "status": "in_progress",
  "location": {
    "latitude": 40.7128,
    "longitude": -74.0060
  },
  "notes": "En route to location"
}
```

**Valid Status Transitions:**
- `pending` → `assigned`
- `assigned` → `in_progress`
- `in_progress` → `completed`
- Any status → `cancelled`

## Field Agent Endpoints

### GET /api/v1/emergency/agent/requests/pending

Get pending requests for field agent.

**Headers:**
```
Authorization: Bearer YOUR_ACCESS_TOKEN
X-Attestation-Token: YOUR_ATTESTATION_TOKEN
X-Platform: android|ios
```

**Response:**
```json
{
  "requests": [
    {
      "request_id": "req_123456789",
      "service_type": "security",
      "priority": "high",
      "location": {
        "latitude": 40.7128,
        "longitude": -74.0060
      },
      "address": "123 Main St, New York, NY",
      "distance_km": 2.5,
      "created_at": "2024-08-24T10:30:00Z",
      "requester_phone": "+1234567890"
    }
  ]
}
```

### POST /api/v1/emergency/agent/requests/{request_id}/accept

Accept an assigned emergency request.

**Headers:**
```
Authorization: Bearer YOUR_ACCESS_TOKEN
X-Attestation-Token: YOUR_ATTESTATION_TOKEN
```

**Request Body:**
```json
{
  "estimated_arrival": "2024-08-24T10:45:00Z",
  "current_location": {
    "latitude": 40.7000,
    "longitude": -74.0100
  }
}
```

**Response:**
```json
{
  "message": "Request accepted successfully",
  "request_id": "req_123456789",
  "estimated_arrival": "2024-08-24T10:45:00Z"
}
```

## Code Examples

### JavaScript - Submit Emergency Request

```javascript
async function submitEmergencyRequest(serviceType, location, address, description, groupId) {
  try {
    const response = await fetch('/api/v1/emergency/request', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'X-Attestation-Token': attestationToken,
        'X-Platform': 'android',
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        service_type: serviceType,
        location: location,
        address: address,
        description: description,
        group_id: groupId
      })
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    console.log('Emergency request submitted:', data.request_id);
    return data;
  } catch (error) {
    console.error('Failed to submit emergency request:', error);
    throw error;
  }
}
```

### Python - Field Agent Accept Request

```python
import requests

def accept_emergency_request(request_id: str, estimated_arrival: str, current_location: dict):
    """Accept an emergency request as a field agent"""
    response = requests.post(
        f"/api/v1/emergency/agent/requests/{request_id}/accept",
        headers={
            "Authorization": f"Bearer {access_token}",
            "X-Attestation-Token": attestation_token,
            "Content-Type": "application/json"
        },
        json={
            "estimated_arrival": estimated_arrival,
            "current_location": current_location
        }
    )
    
    response.raise_for_status()
    return response.json()
```

## Error Handling

Common error responses:

- `400 Bad Request` - Invalid request data or location outside coverage
- `401 Unauthorized` - Invalid or expired token
- `403 Forbidden` - Insufficient permissions or subscription expired
- `404 Not Found` - Request not found
- `409 Conflict` - Request already processed or duplicate
- `423 Locked` - Account locked (panic requests still work for valid subscriptions)

## Real-time Updates

Emergency requests support real-time updates via WebSocket. See [WebSocket API](./websocket.md) for details.

## Security Notes

1. **Location Privacy**: Location data is encrypted and only shared with assigned personnel
2. **Emergency Override**: Panic requests work even with locked accounts if subscription is valid
3. **Attestation Required**: Mobile endpoints require valid app attestation
4. **Rate Limiting**: Emergency requests are rate-limited to prevent abuse (5 per minute)