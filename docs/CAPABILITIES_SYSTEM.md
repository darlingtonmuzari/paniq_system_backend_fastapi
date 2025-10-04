# Emergency Provider Capabilities System

## Overview

The capabilities system provides a normalized way to manage and track what emergency providers can do. It replaces the simple array-based approach with a proper relational database structure that supports detailed capability management.

## Database Structure

### Tables

#### `capabilities`
- `id` (UUID): Primary key
- `name` (String): Human-readable capability name
- `code` (String): Unique identifier for the capability
- `description` (Text): Detailed description of what this capability entails
- `category` (String): Category grouping (medical, security, transport, emergency, law_enforcement)
- `is_active` (Boolean): Whether this capability is currently available
- `created_at` (DateTime): Creation timestamp
- `updated_at` (DateTime): Last modification timestamp

#### `provider_capabilities`
Junction table linking providers to their capabilities:
- `id` (UUID): Primary key
- `provider_id` (UUID): Foreign key to emergency_providers
- `capability_id` (UUID): Foreign key to capabilities
- `proficiency_level` (Enum): BASIC, STANDARD, ADVANCED, EXPERT
- `certification_level` (String): Optional certification details
- `created_at` (DateTime): When capability was assigned
- `updated_at` (DateTime): Last modification

## Capability Categories

### Medical
- Emergency Medical Transport
- Basic Life Support
- Advanced Life Support
- Cardiac Care
- Trauma Care
- Patient Stabilization
- Medical Equipment
- Inter Hospital Transfer
- Emergency Medical Services

### Security
- Armed Response
- Patrol Services
- Alarm Response
- Escort Services
- Crowd Control
- Access Control
- Surveillance

### Transport
- Vehicle Towing
- Roadside Assistance
- Jump Start
- Tire Change
- Lockout Service
- Fuel Delivery
- Accident Recovery
- Heavy Vehicle Towing

### Emergency
- Fire Suppression
- Rescue Operations
- Hazmat Response
- Vehicle Extrication
- Search and Rescue
- Water Rescue
- Technical Rescue

### Law Enforcement
- Law Enforcement
- Emergency Response
- Crime Investigation
- Traffic Control
- Public Safety
- Crisis Intervention
- Emergency Coordination

## API Endpoints

### Capability Management (Admin/Super Admin Only)

#### Create Capability
```
POST /api/v1/capabilities/
```
**Headers:** Authorization: Bearer {admin_token}
**Body:**
```json
{
  "name": "Emergency Medical Transport",
  "code": "emergency_medical_transport",
  "description": "Provide emergency medical transportation services",
  "category": "medical",
  "is_active": true
}
```

#### Get All Capabilities
```
GET /api/v1/capabilities/
```
**Query Parameters:**
- `category` (optional): Filter by category
- `include_inactive` (optional): Include inactive capabilities

#### Get Single Capability
```
GET /api/v1/capabilities/{capability_id}
```

#### Update Capability
```
PUT /api/v1/capabilities/{capability_id}
```
**Headers:** Authorization: Bearer {admin_token}

#### Delete Capability (Soft Delete)
```
DELETE /api/v1/capabilities/{capability_id}
```
**Headers:** Authorization: Bearer {admin_token}

### Provider Capability Management

#### Assign Capability to Provider
```
POST /api/v1/capabilities/provider-capabilities
```
**Headers:** Authorization: Bearer {admin_token}
**Body:**
```json
{
  "provider_id": "uuid",
  "capability_id": "uuid",
  "proficiency_level": "STANDARD",
  "certification_level": "Level 1 Certified"
}
```

#### Get Provider Capabilities
```
GET /api/v1/capabilities/provider-capabilities/{provider_id}
```
**Headers:** Authorization: Bearer {token}

#### Remove Capability from Provider
```
DELETE /api/v1/capabilities/provider-capabilities/{provider_capability_id}
```
**Headers:** Authorization: Bearer {admin_token}

## Proficiency Levels

The system supports four proficiency levels:
- **BASIC**: Entry-level capability
- **STANDARD**: Regular operational capability
- **ADVANCED**: Enhanced capability with additional training
- **EXPERT**: Highest level of capability with specialized expertise

## Role-Based Access Control

### Admin and Super Admin
- Full CRUD access to capabilities
- Can assign/remove capabilities from providers
- Can update proficiency levels and certifications

### All Other Authenticated Users
- Read-only access to capabilities
- Can view provider capabilities
- Cannot modify capability data

## Migration

The migration script (`migrate_to_capabilities_table.py`) automatically:
1. Creates all predefined capabilities in the database
2. Migrates existing provider capabilities from the array format
3. Establishes proper relationships in the junction table
4. Preserves all existing capability assignments

## Usage Examples

### Get all medical capabilities
```bash
curl -H "Authorization: Bearer {token}" \
     "http://localhost:8000/api/v1/capabilities/?category=medical"
```

### Get capabilities for a specific provider
```bash
curl -H "Authorization: Bearer {token}" \
     "http://localhost:8000/api/v1/capabilities/provider-capabilities/{provider_id}"
```

### Assign a new capability to a provider (admin only)
```bash
curl -X POST \
     -H "Authorization: Bearer {admin_token}" \
     -H "Content-Type: application/json" \
     -d '{"provider_id": "uuid", "capability_id": "uuid", "proficiency_level": "ADVANCED"}' \
     "http://localhost:8000/api/v1/capabilities/provider-capabilities"
```

## Benefits of the New System

1. **Normalized Data**: Eliminates duplication and ensures consistency
2. **Detailed Tracking**: Supports proficiency levels and certifications
3. **Flexible Categories**: Easy to add new capability categories
4. **Audit Trail**: Full timestamps for capability assignments
5. **Role-Based Security**: Proper permission controls for modifications
6. **Scalable**: Can easily handle thousands of capabilities and assignments