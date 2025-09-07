# Coverage Area Active Status Feature

## Overview
Added `is_active` field to coverage areas, allowing security firms to activate/deactivate their coverage areas without deleting them. This provides better control over service availability and operational flexibility.

## Key Features

### 1. **Active Status Management**
- Coverage areas can be marked as active (`true`) or inactive (`false`)
- New areas default to active status
- Inactive areas are excluded from subscription validation
- Provides soft disable functionality without data loss

### 2. **Filtering Support**
- API endpoints support filtering by active status
- `include_inactive` parameter controls visibility
- Default behavior includes all areas for backward compatibility

### 3. **Subscription Integration**
- Only active coverage areas are considered for subscription validation
- Inactive areas don't affect user group coverage checks
- Alternative firm discovery only considers active areas

## Database Changes

### Schema Update
```sql
ALTER TABLE coverage_areas 
ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE;
```

### Migration Applied
- ✅ Column added to existing `coverage_areas` table
- ✅ Default value `TRUE` applied to existing records
- ✅ All existing coverage areas remain active

## API Changes

### Updated Models

#### CoverageAreaResponse
```json
{
  "id": "b3734d7f-2de1-4e37-91f6-fca16356d686",
  "name": "Test Coverage Area",
  "boundary_coordinates": [...],
  "is_active": true,                    // ← New field
  "created_at": "2025-09-05T15:43:43.890295+00:00"
}
```

#### CoverageAreaUpdateRequest
```json
{
  "name": "Updated Area Name",          // Optional
  "boundary_coordinates": [...],        // Optional
  "is_active": false                    // ← New optional field
}
```

### Updated Endpoints

#### 1. GET Coverage Areas with Filtering
**GET** `/api/v1/security-firms/{firm_id}/coverage-areas?include_inactive={boolean}`

```bash
# Get only active areas
GET /api/v1/security-firms/{firm_id}/coverage-areas?include_inactive=false

# Get all areas (default)
GET /api/v1/security-firms/{firm_id}/coverage-areas?include_inactive=true
```

#### 2. Update Coverage Area with Active Status
**PUT** `/api/v1/security-firms/{firm_id}/coverage-areas/{area_id}`

```json
{
  "name": "Updated Area",
  "is_active": false
}
```

#### 3. New Convenience Endpoints

##### Activate Coverage Area
**PUT** `/api/v1/security-firms/{firm_id}/coverage-areas/{area_id}/activate`

Sets `is_active = true` for the specified coverage area.

##### Deactivate Coverage Area
**PUT** `/api/v1/security-firms/{firm_id}/coverage-areas/{area_id}/deactivate`

Sets `is_active = false` for the specified coverage area.

## Service Layer Changes

### Updated Methods

#### `get_coverage_areas()`
```python
async def get_coverage_areas(
    self, 
    firm_id: str, 
    user_id: str, 
    include_inactive: bool = True  # ← New parameter
) -> List[CoverageArea]:
```

#### `update_coverage_area()`
```python
async def update_coverage_area(
    self,
    firm_id: str,
    area_id: str,
    name: Optional[str] = None,
    boundary_coordinates: Optional[List[List[float]]] = None,
    is_active: Optional[bool] = None,  # ← New parameter
    user_id: str = None
) -> CoverageArea:
```

### Subscription Validation Updates

#### Only Active Areas Considered
```python
# Updated query to only consider active coverage areas
result = await self.db.execute(
    select(CoverageArea).where(
        and_(
            CoverageArea.firm_id == firm_id,
            CoverageArea.is_active == True  # ← New condition
        )
    )
)
```

## Usage Examples

### 1. Create Coverage Area (Defaults to Active)
```bash
curl -X POST "http://localhost:8000/api/v1/security-firms/{FIRM_ID}/coverage-areas" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Business District",
    "boundary_coordinates": [
      [28.0400, -26.1100],
      [28.0500, -26.1100],
      [28.0500, -26.1000],
      [28.0400, -26.1000],
      [28.0400, -26.1100]
    ]
  }'
```

**Response**:
```json
{
  "id": "area-id",
  "name": "Business District",
  "boundary_coordinates": [...],
  "is_active": true,
  "created_at": "2025-09-05T15:43:43.890295+00:00"
}
```

### 2. Deactivate Coverage Area
```bash
curl -X PUT "http://localhost:8000/api/v1/security-firms/{FIRM_ID}/coverage-areas/{AREA_ID}" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "is_active": false
  }'
```

### 3. Use Convenience Endpoint
```bash
# Deactivate
curl -X PUT "http://localhost:8000/api/v1/security-firms/{FIRM_ID}/coverage-areas/{AREA_ID}/deactivate" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Activate
curl -X PUT "http://localhost:8000/api/v1/security-firms/{FIRM_ID}/coverage-areas/{AREA_ID}/activate" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 4. Filter by Active Status
```bash
# Get only active areas
curl -X GET "http://localhost:8000/api/v1/security-firms/{FIRM_ID}/coverage-areas?include_inactive=false" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Get all areas
curl -X GET "http://localhost:8000/api/v1/security-firms/{FIRM_ID}/coverage-areas?include_inactive=true" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Business Logic Impact

### 1. **Subscription Validation**
- ✅ Only active coverage areas are checked for user group locations
- ✅ Inactive areas don't affect subscription eligibility
- ✅ Users can't subscribe to services in inactive coverage areas

### 2. **Alternative Firm Discovery**
- ✅ Only active coverage areas are considered when finding alternative firms
- ✅ Inactive areas don't appear in location-based firm searches

### 3. **Team Management**
- Coverage areas can be deactivated even with associated teams
- Teams remain associated but area becomes non-operational
- Reactivation restores full functionality

## Use Cases

### 1. **Temporary Service Suspension**
```bash
# Temporarily suspend service in an area
PUT /coverage-areas/{area_id}/deactivate

# Later restore service
PUT /coverage-areas/{area_id}/activate
```

### 2. **Maintenance Mode**
```bash
# Disable area during maintenance
PUT /coverage-areas/{area_id} -d '{"is_active": false}'

# Re-enable after maintenance
PUT /coverage-areas/{area_id} -d '{"is_active": true}'
```

### 3. **Gradual Service Rollout**
```bash
# Create area as inactive initially
POST /coverage-areas -d '{"name": "New Area", "boundary_coordinates": [...], "is_active": false}'

# Activate when ready to provide service
PUT /coverage-areas/{area_id}/activate
```

### 4. **Operational Flexibility**
```bash
# Get only operational areas for dashboard
GET /coverage-areas?include_inactive=false

# Get all areas for management interface
GET /coverage-areas?include_inactive=true
```

## Testing Results

✅ **Create**: New areas default to active status  
✅ **Update**: Can update active status individually or with other fields  
✅ **Filtering**: Active-only filtering works correctly  
✅ **Convenience Endpoints**: Activate/deactivate endpoints work  
✅ **Combined Updates**: Can update name, boundary, and status together  
✅ **Subscription Integration**: Only active areas considered for validation  
✅ **Database Migration**: Existing areas migrated successfully  

## Backward Compatibility

- ✅ **API Compatibility**: All existing endpoints continue to work
- ✅ **Default Behavior**: New areas are active by default
- ✅ **Existing Data**: All existing coverage areas remain active
- ✅ **Response Format**: New `is_active` field added to responses
- ✅ **Query Parameters**: `include_inactive` parameter is optional

## Performance Impact

- **Minimal Overhead**: Single boolean field addition
- **Indexed Queries**: Can add index on `is_active` if needed
- **Efficient Filtering**: Simple boolean condition in WHERE clauses
- **No Breaking Changes**: Existing queries continue to work

The active status feature provides operational flexibility while maintaining full backward compatibility and data integrity.