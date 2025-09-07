#!/usr/bin/env python3
"""
Example showing how areas are represented at different levels
"""
from shapely.geometry import Polygon
from geoalchemy2.shape import from_shape, to_shape
import json

def demonstrate_area_representation():
    """Show how areas are represented at different levels"""
    
    print("🗺️  Area Representation Example")
    print("=" * 50)
    
    # 1. API Level - JSON coordinates
    print("\n1. API Level (JSON Input):")
    api_coordinates = [
        [28.0473, -26.2041],  # Johannesburg CBD - Point 1
        [28.0573, -26.2041],  # Point 2
        [28.0573, -26.1941],  # Point 3
        [28.0473, -26.1941],  # Point 4
        [28.0473, -26.2041]   # Closing point (same as first)
    ]
    
    api_request = {
        "name": "Johannesburg CBD Area",
        "boundary_coordinates": api_coordinates
    }
    
    print(f"Request JSON:")
    print(json.dumps(api_request, indent=2))
    
    # 2. Application Level - Shapely Polygon
    print("\n2. Application Level (Shapely Polygon):")
    polygon = Polygon(api_coordinates)
    
    print(f"Polygon Type: {type(polygon)}")
    print(f"Is Valid: {polygon.is_valid}")
    print(f"Area (sq degrees): {polygon.area:.8f}")
    print(f"Bounds (minx, miny, maxx, maxy): {polygon.bounds}")
    print(f"Centroid: {polygon.centroid}")
    print(f"Number of Points: {len(polygon.exterior.coords)}")
    
    # 3. Database Level - PostGIS Geometry
    print("\n3. Database Level (PostGIS Geometry):")
    
    # Convert to PostGIS geometry (this is what gets stored)
    postgis_geometry = from_shape(polygon, srid=4326)
    print(f"PostGIS Type: {type(postgis_geometry)}")
    print(f"SRID: 4326 (WGS84)")
    
    # Well-Known Text representation (how PostGIS stores it internally)
    wkt_representation = polygon.wkt
    print(f"WKT Format: {wkt_representation}")
    
    # 4. Response Level - Convert back to coordinates
    print("\n4. API Response (Converted back to coordinates):")
    
    # This is what happens when reading from database
    retrieved_polygon = to_shape(postgis_geometry)
    response_coordinates = list(retrieved_polygon.exterior.coords)
    
    response_data = {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "name": "Johannesburg CBD Area",
        "boundary_coordinates": response_coordinates,
        "created_at": "2025-09-05T10:30:00Z"
    }
    
    print(json.dumps(response_data, indent=2, default=str))
    
    # 5. Geometric Properties
    print("\n5. Geometric Properties:")
    print(f"Area in square degrees: {polygon.area:.8f}")
    
    # Convert to approximate square kilometers (rough calculation)
    # Note: This is approximate because degrees vary by latitude
    import math
    
    lat_center = sum(coord[1] for coord in api_coordinates[:-1]) / (len(api_coordinates) - 1)
    km_per_degree_lat = 111.32  # Approximately constant
    km_per_degree_lon = 111.32 * abs(math.cos(math.radians(lat_center)))  # Varies by latitude
    
    area_sq_km = polygon.area * km_per_degree_lat * km_per_degree_lon
    print(f"Approximate area in sq km: {area_sq_km:.2f}")
    
    # 6. Validation Examples
    print("\n6. Validation Examples:")
    
    # Valid polygon
    valid_coords = [[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]
    valid_polygon = Polygon(valid_coords)
    print(f"Valid rectangle: {valid_polygon.is_valid}")
    
    # Invalid polygon (self-intersecting)
    invalid_coords = [[0, 0], [1, 1], [1, 0], [0, 1], [0, 0]]
    invalid_polygon = Polygon(invalid_coords)
    print(f"Self-intersecting polygon: {invalid_polygon.is_valid}")
    
    # Too few points
    try:
        too_few_coords = [[0, 0], [1, 0]]
        Polygon(too_few_coords)
    except Exception as e:
        print(f"Too few coordinates error: {type(e).__name__}")

def show_real_world_examples():
    """Show real-world area examples"""
    
    print("\n\n🌍 Real-World Examples")
    print("=" * 50)
    
    examples = {
        "Small Neighborhood": {
            "description": "Residential area in Sandton",
            "coordinates": [
                [28.0436, -26.1076],  # Southwest corner
                [28.0536, -26.1076],  # Southeast corner  
                [28.0536, -26.0976],  # Northeast corner
                [28.0436, -26.0976],  # Northwest corner
                [28.0436, -26.1076]   # Close polygon
            ]
        },
        "Shopping Mall Area": {
            "description": "Area around Sandton City Mall",
            "coordinates": [
                [28.0500, -26.1070],
                [28.0520, -26.1070],
                [28.0520, -26.1050],
                [28.0500, -26.1050],
                [28.0500, -26.1070]
            ]
        },
        "Industrial Zone": {
            "description": "Industrial area in Germiston",
            "coordinates": [
                [28.1500, -26.2300],
                [28.1700, -26.2300],
                [28.1700, -26.2100],
                [28.1500, -26.2100],
                [28.1500, -26.2300]
            ]
        }
    }
    
    for name, data in examples.items():
        print(f"\n{name}:")
        print(f"Description: {data['description']}")
        
        polygon = Polygon(data['coordinates'])
        print(f"Area: {polygon.area:.8f} sq degrees")
        print(f"Bounds: {polygon.bounds}")
        
        # Calculate approximate dimensions
        bounds = polygon.bounds
        width_degrees = bounds[2] - bounds[0]  # maxx - minx
        height_degrees = bounds[3] - bounds[1]  # maxy - miny
        
        # Rough conversion to meters (at Johannesburg latitude)
        width_meters = width_degrees * 111320 * abs(math.cos(math.radians(-26.2)))
        height_meters = height_degrees * 111320
        
        print(f"Approximate size: {width_meters:.0f}m × {height_meters:.0f}m")

if __name__ == "__main__":
    import math
    demonstrate_area_representation()
    show_real_world_examples()