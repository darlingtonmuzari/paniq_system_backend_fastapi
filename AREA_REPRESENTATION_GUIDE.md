# How Areas Are Represented in the Coverage System

## Overview
Areas in the coverage system are represented as **polygons** using geographic coordinates. The system handles multiple representation formats as data flows from API requests to database storage.

## 1. API Level - JSON Coordinates

### Input Format
```json
{
  "name": "Johannesburg CBD Area",
  "boundary_coordinates": [
    [28.0473, -26.2041],  // [longitude, latitude]
    [28.0573, -26.2041],  // Point 2
    [28.0573, -26.1941],  // Point 3
    [28.0473, -26.1941],  // Point 4
    [28.0473, -26.2041]   // Closing point (same as first)
  ]
}
```

### Key Rules
- **Coordinate Order**: `[longitude, latitude]` (X, Y)
- **Minimum Points**: 3 unique points + 1 closing point (4 total)
- **Polygon Closure**: First and last coordinates must be identical
- **Coordinate System**: WGS84 (SRID 4326)

### South African Coordinate Ranges
```
Longitude: 16°E to 33°E  (16.0 to 33.0)
Latitude:  22°S to 35°S  (-22.0 to -35.0)

Example Johannesburg: [28.0473, -26.2041]
                     [  East  ,  South  ]
```

## 2. Application Level - Shapely Polygon

### Conversion Process
```python
from shapely.geometry import Polygon

# Create polygon from coordinates
coordinates = [[28.0473, -26.2041], [28.0573, -26.2041], 
               [28.0573, -26.1941], [28.0473, -26.1941], 
               [28.0473, -26.2041]]
polygon = Polygon(coordinates)

# Available properties
polygon.area          # 0.00010000 (square degrees)
polygon.bounds        # (minx, miny, maxx, maxy)
polygon.centroid      # Center point
polygon.is_valid      # True/False
polygon.exterior      # Boundary coordinates
```

### Geometric Properties
- **Area**: Calculated in square degrees
- **Bounds**: Bounding rectangle (min/max coordinates)
- **Centroid**: Geographic center point
- **Validity**: Checks for self-intersection, proper closure

## 3. Database Level - PostGIS Geometry

### Storage Format
```sql
CREATE TABLE coverage_areas (
    id UUID PRIMARY KEY,
    firm_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    boundary GEOMETRY(POLYGON, 4326) NOT NULL  -- PostGIS geometry
);
```

### Well-Known Text (WKT) Format
```
POLYGON((28.0473 -26.2041, 28.0573 -26.2041, 28.0573 -26.1941, 28.0473 -26.1941, 28.0473 -26.2041))
```

### PostGIS Features
- **Spatial Indexing**: GIST index for fast geographic queries
- **Spatial Functions**: `ST_Within`, `ST_Contains`, `ST_Intersects`
- **Coordinate Transformations**: Support for different coordinate systems

## 4. Real-World Size Examples

### Small Areas
```json
// Shopping Mall Area (200m × 223m)
{
  "name": "Sandton City Mall Area",
  "boundary_coordinates": [
    [28.0500, -26.1070],
    [28.0520, -26.1070],
    [28.0520, -26.1050],
    [28.0500, -26.1050],
    [28.0500, -26.1070]
  ]
}
```
- **Area**: 0.000004 square degrees
- **Approximate Size**: 200m × 223m
- **Use Case**: Single building or small complex

### Medium Areas
```json
// Neighborhood Area (999m × 1113m)
{
  "name": "Sandton Residential Area",
  "boundary_coordinates": [
    [28.0436, -26.1076],
    [28.0536, -26.1076],
    [28.0536, -26.0976],
    [28.0436, -26.0976],
    [28.0436, -26.1076]
  ]
}
```
- **Area**: 0.0001 square degrees
- **Approximate Size**: 999m × 1113m (≈1.11 km²)
- **Use Case**: Residential neighborhood

### Large Areas
```json
// Industrial Zone (1998m × 2226m)
{
  "name": "Germiston Industrial Area",
  "boundary_coordinates": [
    [28.1500, -26.2300],
    [28.1700, -26.2300],
    [28.1700, -26.2100],
    [28.1500, -26.2100],
    [28.1500, -26.2300]
  ]
}
```
- **Area**: 0.0004 square degrees
- **Approximate Size**: 1998m × 2226m (≈4.45 km²)
- **Use Case**: Industrial or commercial district

## 5. Coordinate System Details

### WGS84 (SRID 4326)
- **Global Standard**: Used by GPS, Google Maps, etc.
- **Units**: Decimal degrees
- **Precision**: ~1 meter at equator per 0.00001 degrees

### Coordinate Precision
```
Decimal Places | Precision at Johannesburg Latitude
0.1           | ~11 km
0.01          | ~1.1 km
0.001         | ~111 m
0.0001        | ~11 m
0.00001       | ~1.1 m
0.000001      | ~0.11 m (11 cm)
```

## 6. Validation Rules

### Valid Polygon Requirements
1. **Minimum 3 unique points** (plus closing point)
2. **Closed polygon** (first point = last point)
3. **No self-intersections**
4. **Proper winding order** (counter-clockwise for exterior)

### Examples

#### ✅ Valid Rectangle
```json
[
  [0, 0], [1, 0], [1, 1], [0, 1], [0, 0]
]
```

#### ❌ Invalid - Self-Intersecting
```json
[
  [0, 0], [1, 1], [1, 0], [0, 1], [0, 0]
]
```

#### ❌ Invalid - Too Few Points
```json
[
  [0, 0], [1, 0]
]
```

#### ❌ Invalid - Not Closed
```json
[
  [0, 0], [1, 0], [1, 1], [0, 1]
]
```

## 7. Data Flow Summary

```
API Request (JSON)
    ↓
Validation & Parsing
    ↓
Shapely Polygon (Python)
    ↓
PostGIS Geometry (Database)
    ↓
Spatial Indexing & Storage
    ↓
Query & Retrieval
    ↓
Shapely Polygon (Python)
    ↓
JSON Response (API)
```

## 8. Common Use Cases

### Security Firm Coverage
```json
{
  "name": "Rosebank Business District",
  "boundary_coordinates": [
    [28.0400, -26.1500],
    [28.0500, -26.1500],
    [28.0500, -26.1400],
    [28.0400, -26.1400],
    [28.0400, -26.1500]
  ]
}
```

### Subscription Validation
```python
# Check if user group is within coverage area
result = await db.execute(
    select(func.count()).where(
        ST_Within(group.location, coverage_area.boundary)
    )
)
is_covered = result.scalar() > 0
```

### Alternative Firm Discovery
```python
# Find firms covering a specific location
point_wkt = f"POINT({longitude} {latitude})"
result = await db.execute(
    select(SecurityFirm, CoverageArea).join(
        CoverageArea, SecurityFirm.id == CoverageArea.firm_id
    ).where(
        ST_Within(ST_GeomFromText(point_wkt, 4326), CoverageArea.boundary)
    )
)
```

## 9. Performance Considerations

### Spatial Indexing
```sql
-- Automatically created for efficient spatial queries
CREATE INDEX idx_coverage_areas_boundary 
ON coverage_areas USING GIST (boundary);
```

### Query Optimization
- Use spatial functions for geographic operations
- Leverage PostGIS indexing for fast lookups
- Consider polygon complexity for performance

## 10. Best Practices

### Coordinate Precision
- Use 4-6 decimal places for meter-level precision
- Avoid excessive precision that doesn't add value

### Polygon Complexity
- Keep polygons simple for better performance
- Use appropriate level of detail for the use case

### Validation
- Always validate coordinates before storage
- Check for geometric validity using Shapely
- Ensure proper polygon closure

This representation system provides a robust foundation for managing geographic coverage areas with proper validation, efficient storage, and fast spatial queries.