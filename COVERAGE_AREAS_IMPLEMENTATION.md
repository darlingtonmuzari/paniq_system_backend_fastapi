# Coverage Areas API Implementation

## Overview
The `http://localhost:8000/api/v1/security-firms/{FIRM_ID}/coverage-areas` endpoint allows security firms to define and manage their service coverage areas using geographic boundaries (polygons).

## API Endpoints

### 1. GET `/api/v1/security-firms/{firm_id}/coverage-areas`
**Purpose**: Retrieve all coverage areas for a specific security firm

**Implementation Flow**:
```
API Layer → SecurityFirmService → Database → PostGIS
```

### 2. POST `/api/v1/security-firms/{firm_id}/coverage-areas`
**Purpose**: Create a new coverage area for a security firm

## Technical Architecture

### 1. API Layer (`app/api/v1/security_firms.py`)

#### GET Endpoint
```python
@router.get("/{firm_id}/coverage-areas", response_model=List[CoverageAreaResponse])
async def get_coverage_areas(
    firm_id: str,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
```

**Process**:
1. Validates user authentication
2. Calls `SecurityFirmService.get_coverage_areas()`
3. Converts PostGIS geometry to coordinate arrays
4. Returns list of coverage areas with coordinates

#### POST Endpoint
```python
@router.post("/{firm_id}/coverage-areas", response_model=CoverageAreaResponse)
async def create_coverage_area(
    firm_id: str,
    request: CoverageAreaRequest,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
```

**Process**:
1. Validates user authentication
2. Validates polygon coordinates
3. Calls `SecurityFirmService.create_coverage_area()`
4. Converts geometry back to coordinates for response

### 2. Service Layer (`app/services/security_firm.py`)

#### `get_coverage_areas()` Method
```python
async def get_coverage_areas(self, firm_id: str, user_id: str) -> List[CoverageArea]:
    # Verify firm exists
    firm = await self.db.get(SecurityFirm, firm_id)
    if not firm:
        raise ValueError("Security firm not found")
    
    # TODO: Add authorization check
    
    result = await self.db.execute(
        select(CoverageArea).where(CoverageArea.firm_id == firm_id)
    )
    return result.scalars().all()
```

#### `create_coverage_area()` Method
```python
async def create_coverage_area(
    self,
    firm_id: str,
    name: str,
    boundary_coordinates: List[List[float]],
    user_id: str
) -> CoverageArea:
    # 1. Verify firm exists and is approved
    firm = await self.db.get(SecurityFirm, firm_id)
    if not firm:
        raise ValueError("Security firm not found")
    
    if firm.verification_status != "approved":
        raise ValueError("Security firm must be approved to create coverage areas")
    
    # 2. Create and validate polygon
    try:
        polygon = Polygon(boundary_coordinates)
        if not polygon.is_valid:
            raise ValueError("Invalid polygon coordinates")
    except Exception as e:
        raise ValueError(f"Invalid polygon coordinates: {str(e)}")
    
    # 3. Create coverage area with PostGIS geometry
    coverage_area = CoverageArea(
        firm_id=firm_id,
        name=name,
        boundary=from_shape(polygon, srid=4326)  # Convert to PostGIS geometry
    )
    
    # 4. Save to database
    self.db.add(coverage_area)
    await self.db.commit()
    await self.db.refresh(coverage_area)
    
    return coverage_area
```

### 3. Data Models (`app/models/security_firm.py`)

#### CoverageArea Model
```python
class CoverageArea(BaseModel):
    """Coverage area model with PostGIS geometry"""
    __tablename__ = "coverage_areas"
    
    firm_id = Column(UUID(as_uuid=True), ForeignKey("security_firms.id"), nullable=False)
    name = Column(String(255), nullable=False)
    boundary = Column(Geometry("POLYGON", srid=4326), nullable=False)  # PostGIS geometry
    
    # Relationships
    firm = relationship("SecurityFirm", back_populates="coverage_areas")
    teams = relationship("Team", back_populates="coverage_area")
```

### 4. Request/Response Models

#### CoverageAreaRequest
```python
class CoverageAreaRequest(BaseModel):
    """Coverage area creation request"""
    name: str
    boundary_coordinates: List[List[float]]  # List of [lng, lat] coordinates
    
    @validator('boundary_coordinates')
    def validate_boundary(cls, v):
        if len(v) < 3:
            raise ValueError('Boundary must have at least 3 coordinates')
        # Ensure polygon is closed
        if v[0] != v[-1]:
            v.append(v[0])
        return v
```

#### CoverageAreaResponse
```python
class CoverageAreaResponse(BaseModel):
    """Coverage area response model"""
    id: str
    name: str
    boundary_coordinates: List[List[float]]
    created_at: str
```

## Geographic Data Handling

### 1. Coordinate System
- **SRID 4326**: WGS84 (World Geodetic System 1984)
- **Format**: [longitude, latitude] pairs
- **Storage**: PostGIS POLYGON geometry

### 2. Coordinate Conversion Process

#### Input → Storage
```python
# 1. Receive coordinates as List[List[float]]
boundary_coordinates = [[lng1, lat1], [lng2, lat2], [lng3, lat3], [lng1, lat1]]

# 2. Create Shapely polygon
polygon = Polygon(boundary_coordinates)

# 3. Convert to PostGIS geometry
boundary = from_shape(polygon, srid=4326)
```

#### Storage → Output
```python
# 1. Get PostGIS geometry from database
coverage_area = await db.get(CoverageArea, area_id)

# 2. Convert to Shapely polygon
from geoalchemy2.shape import to_shape
polygon = to_shape(coverage_area.boundary)

# 3. Extract coordinates
coordinates = list(polygon.exterior.coords)
```

## Database Schema

### coverage_areas Table
```sql
CREATE TABLE coverage_areas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    firm_id UUID NOT NULL REFERENCES security_firms(id),
    name VARCHAR(255) NOT NULL,
    boundary GEOMETRY(POLYGON, 4326) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Spatial index for efficient geographic queries
CREATE INDEX idx_coverage_areas_boundary ON coverage_areas USING GIST (boundary);
```

## Usage Examples

### 1. Create Coverage Area
```bash
curl -X POST "http://localhost:8000/api/v1/security-firms/{FIRM_ID}/coverage-areas" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Downtown Area",
    "boundary_coordinates": [
      [-26.2041, 28.0473],
      [-26.2041, 28.0573],
      [-26.1941, 28.0573],
      [-26.1941, 28.0473],
      [-26.2041, 28.0473]
    ]
  }'
```

### 2. Get Coverage Areas
```bash
curl -X GET "http://localhost:8000/api/v1/security-firms/{FIRM_ID}/coverage-areas" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response**:
```json
[
  {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "name": "Downtown Area",
    "boundary_coordinates": [
      [-26.2041, 28.0473],
      [-26.2041, 28.0573],
      [-26.1941, 28.0573],
      [-26.1941, 28.0473],
      [-26.2041, 28.0473]
    ],
    "created_at": "2025-09-05T10:30:00Z"
  }
]
```

## Key Features

### 1. **Geographic Validation**
- Validates polygon has at least 3 coordinates
- Ensures polygon is geometrically valid
- Automatically closes polygon if not closed

### 2. **Authorization**
- Requires user authentication
- Firm must be approved to create coverage areas
- TODO: Add proper user-firm association checks

### 3. **PostGIS Integration**
- Uses PostGIS for efficient spatial operations
- Supports complex geographic queries
- Spatial indexing for performance

### 4. **Coordinate System Support**
- WGS84 (SRID 4326) for global compatibility
- Proper coordinate transformation handling

## Integration with Other Features

### 1. **Subscription Validation**
Used in `SubscriptionService._validate_group_coverage()`:
```python
async def _validate_group_coverage(self, group: UserGroup, firm_id: str) -> bool:
    # Get firm's coverage areas
    result = await self.db.execute(
        select(CoverageArea).where(CoverageArea.firm_id == firm_id)
    )
    coverage_areas = result.scalars().all()
    
    # Check if group location is within any coverage area
    for coverage_area in coverage_areas:
        result = await self.db.execute(
            select(func.count()).where(
                ST_Within(group.location, coverage_area.boundary)
            )
        )
        if result.scalar() > 0:
            return True
    
    return False
```

### 2. **Alternative Firm Discovery**
Used to find alternative firms for locations outside current coverage.

## Security Considerations

1. **Authentication Required**: All endpoints require valid JWT token
2. **Firm Approval**: Only approved firms can create coverage areas
3. **Authorization**: Users should be associated with the firm (TODO: implement)
4. **Input Validation**: Coordinates are validated for geometric validity

## Performance Optimizations

1. **Spatial Indexing**: PostGIS GIST index on boundary column
2. **Efficient Queries**: Uses PostGIS spatial functions for fast lookups
3. **Caching**: Could be added for frequently accessed coverage areas

This implementation provides a robust foundation for managing security firm coverage areas with proper geographic data handling and spatial operations.