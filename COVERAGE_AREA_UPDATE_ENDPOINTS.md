# Coverage Area Update and Delete Endpoints

## Overview
Added new endpoints to support full CRUD operations for coverage areas, allowing security firms to update and delete their coverage areas after creation.

## New Endpoints

### 1. Update Coverage Area
**PUT** `/api/v1/security-firms/{firm_id}/coverage-areas/{area_id}`

Updates an existing coverage area with new name and/or boundary coordinates.

#### Request Body
```json
{
  "name": "Updated Area Name",                    // Optional
  "boundary_coordinates": [                       // Optional
    [28.0400, -26.1100],
    [28.0500, -26.1100],
    [28.0500, -26.1000],
    [28.0400, -26.1000],
    [28.0400, -26.1100]
  ]
}
```

#### Response
```json
{
  "id": "373cdc2b-eba2-4c7f-9634-9d8889ee3591",
  "name": "Updated Area Name",
  "boundary_coordinates": [
    [28.0400, -26.1100],
    [28.0500, -26.1100],
    [28.0500, -26.1000],
    [28.0400, -26.1000],
    [28.0400, -26.1100]
  ],
  "created_at": "2025-09-05T15:27:07.720041+00:00"
}
```

#### Features
- **Partial Updates**: Only provided fields are updated
- **Name Only**: Update just the area name
- **Boundary Only**: Update just the coordinates
- **Both**: Update name and boundary together
- **Validation**: Same coordinate validation as creation

### 2. Delete Coverage Area
**DELETE** `/api/v1/security-firms/{firm_id}/coverage-areas/{area_id}`

Permanently deletes a coverage area.

#### Response
```json
{
  "message": "Coverage area deleted successfully"
}
```

#### Safety Checks
- Prevents deletion if teams are associated with the area
- Verifies area belongs to the specified firm
- Requires proper authentication

## Implementation Details

### API Layer Updates

#### New Request Model
```python
class CoverageAreaUpdateRequest(BaseModel):
    """Coverage area update request"""
    name: Optional[str] = None
    boundary_coordinates: Optional[List[List[float]]] = None
    
    @validator('boundary_coordinates')
    def validate_boundary(cls, v):
        if v is not None:
            if len(v) < 3:
                raise ValueError('Boundary must have at least 3 coordinates')
            if v[0] != v[-1]:
                v.append(v[0])
        return v
```

#### Update Endpoint
```python
@router.put("/{firm_id}/coverage-areas/{area_id}", response_model=CoverageAreaResponse)
async def update_coverage_area(
    firm_id: str,
    area_id: str,
    request: CoverageAreaUpdateRequest,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
```

#### Delete Endpoint
```python
@router.delete("/{firm_id}/coverage-areas/{area_id}")
async def delete_coverage_area(
    firm_id: str,
    area_id: str,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
```

### Service Layer Updates

#### Update Method
```python
async def update_coverage_area(
    self,
    firm_id: str,
    area_id: str,
    name: Optional[str] = None,
    boundary_coordinates: Optional[List[List[float]]] = None,
    user_id: str = None
) -> CoverageArea:
```

**Process**:
1. Verify firm exists and is approved
2. Get existing coverage area
3. Verify area belongs to firm
4. Update name if provided
5. Update boundary if provided (with validation)
6. Save changes to database

#### Delete Method
```python
async def delete_coverage_area(
    self,
    firm_id: str,
    area_id: str,
    user_id: str
) -> bool:
```

**Process**:
1. Verify firm exists
2. Get existing coverage area
3. Verify area belongs to firm
4. Check for associated teams (prevents deletion)
5. Delete from database

## Usage Examples

### Update Area Name Only
```bash
curl -X PUT "http://localhost:8000/api/v1/security-firms/{FIRM_ID}/coverage-areas/{AREA_ID}" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "New Area Name"
  }'
```

### Update Boundary Only
```bash
curl -X PUT "http://localhost:8000/api/v1/security-firms/{FIRM_ID}/coverage-areas/{AREA_ID}" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "boundary_coordinates": [
      [28.0350, -26.1150],
      [28.0550, -26.1150],
      [28.0550, -26.0950],
      [28.0350, -26.0950],
      [28.0350, -26.1150]
    ]
  }'
```

### Update Both Name and Boundary
```bash
curl -X PUT "http://localhost:8000/api/v1/security-firms/{FIRM_ID}/coverage-areas/{AREA_ID}" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Expanded Business District",
    "boundary_coordinates": [
      [28.0300, -26.1200],
      [28.0600, -26.1200],
      [28.0600, -26.0900],
      [28.0300, -26.0900],
      [28.0300, -26.1200]
    ]
  }'
```

### Delete Coverage Area
```bash
curl -X DELETE "http://localhost:8000/api/v1/security-firms/{FIRM_ID}/coverage-areas/{AREA_ID}" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Complete CRUD Operations

Now coverage areas support full CRUD operations:

| Operation | Method | Endpoint | Description |
|-----------|--------|----------|-------------|
| **Create** | POST | `/{firm_id}/coverage-areas` | Create new coverage area |
| **Read** | GET | `/{firm_id}/coverage-areas` | Get all coverage areas |
| **Update** | PUT | `/{firm_id}/coverage-areas/{area_id}` | Update existing area |
| **Delete** | DELETE | `/{firm_id}/coverage-areas/{area_id}` | Delete coverage area |

## Validation and Error Handling

### Update Validation
- **Area Existence**: Verifies area exists before updating
- **Firm Ownership**: Ensures area belongs to specified firm
- **Coordinate Validation**: Same rules as creation (min 3 points, closed polygon)
- **Geometric Validity**: Uses Shapely to validate polygon geometry

### Delete Validation
- **Area Existence**: Verifies area exists before deletion
- **Firm Ownership**: Ensures area belongs to specified firm
- **Team Dependencies**: Prevents deletion if teams are associated
- **Authorization**: Requires proper user permissions

### Error Responses

#### Area Not Found (400)
```json
{
  "error_code": "HTTP_400",
  "message": "Coverage area not found",
  "details": {},
  "timestamp": "2025-09-05T15:27:08.200246",
  "request_id": null
}
```

#### Invalid Coordinates (422)
```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "boundary_coordinates"],
      "msg": "Value error, Boundary must have at least 3 coordinates",
      "input": [[28.04, -26.11], [28.05, -26.11]],
      "ctx": {"error": {}},
      "url": "https://errors.pydantic.dev/2.5/v/value_error"
    }
  ]
}
```

#### Cannot Delete (400)
```json
{
  "error_code": "HTTP_400",
  "message": "Cannot delete coverage area that has 2 team(s) associated with it. Please reassign or remove the teams first.",
  "details": {},
  "timestamp": "2025-09-05T15:27:08.200246",
  "request_id": null
}
```

## Testing Results

✅ **Update Name Only**: Successfully updates area name while preserving boundary
✅ **Update Boundary Only**: Successfully updates coordinates while preserving name  
✅ **Update Both**: Successfully updates both name and boundary together
✅ **Delete Area**: Successfully removes coverage area from database
✅ **Error Handling**: Proper validation and error messages for invalid requests
✅ **Authorization**: Requires authentication and firm ownership verification

## Security Features

1. **Authentication Required**: All endpoints require valid JWT token
2. **Firm Verification**: Only approved firms can update/delete coverage areas
3. **Ownership Validation**: Users can only modify their firm's coverage areas
4. **Dependency Checks**: Prevents deletion of areas with associated teams
5. **Input Validation**: Comprehensive validation of coordinates and data

## Performance Considerations

- **Efficient Updates**: Only updates provided fields, minimizes database operations
- **Spatial Validation**: Uses Shapely for fast geometric validation
- **Database Constraints**: Leverages foreign key constraints for data integrity
- **Indexed Queries**: Benefits from existing spatial indexes on boundary column

The coverage area endpoints now provide complete CRUD functionality with proper validation, error handling, and security measures.