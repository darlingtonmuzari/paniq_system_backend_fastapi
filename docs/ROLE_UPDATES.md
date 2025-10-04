# Role System Updates

## Overview
The role system has been updated to provide better clarity and hierarchy for firm personnel roles.

## Changes Made

### Role Renaming
- **`office_staff`** → **`firm_user`**
  - Basic firm personnel with standard access permissions
  - Can view and manage basic firm operations
  - Cannot perform administrative actions

### New Role Added
- **`firm_supervisor`**
  - Elevated permissions above `firm_user`
  - Can perform administrative actions like fines and suspensions
  - Can manage other firm personnel (except firm_admin)
  - Has access to statistics and reporting features

## Updated Role Hierarchy

### FirmPersonnel Roles
1. **`field_agent`** - Field operatives who respond to emergencies
2. **`team_leader`** - Leads teams of field agents
3. **`firm_user`** - Basic office personnel (formerly office_staff)
4. **`firm_supervisor`** - Supervisory office personnel (new)

### FirmUser Roles
1. **`field_staff`** - Field-based staff
2. **`firm_user`** - Basic firm users (formerly office_staff)
3. **`firm_supervisor`** - Supervisory firm users (new)
4. **`firm_admin`** - Firm administrators

## Permission Changes

### Emergency System
- **Request Allocation**: `firm_user`, `firm_supervisor`, `team_leader`
- **Call Handling**: `firm_user`, `firm_supervisor`
- **Request Reassignment**: `firm_user`, `firm_supervisor`, `team_leader`

### Prank Detection System
- **View Prank Data**: `firm_user`, `firm_supervisor`, `admin`
- **Calculate Fines**: `firm_supervisor` only (elevated from office_staff)
- **Suspend Accounts**: `firm_supervisor` only (elevated from office_staff)
- **View Statistics**: `firm_supervisor` only (elevated from office_staff)

## Migration

### Database Migration
Run the migration to update existing records:
```bash
alembic upgrade head
```

This will:
- Update all `office_staff` roles to `firm_user` in both `firm_personnel` and `firm_users` tables
- Preserve all existing permissions for renamed roles
- Make `firm_supervisor` role available for new assignments

### Manual Role Updates
After migration, you may want to promote some `firm_user` accounts to `firm_supervisor`:

```sql
-- Example: Promote specific users to supervisor role
UPDATE firm_personnel 
SET role = 'firm_supervisor' 
WHERE email IN ('supervisor1@firm.com', 'supervisor2@firm.com');

UPDATE firm_users 
SET role = 'firm_supervisor' 
WHERE user_id IN (SELECT id FROM registered_users WHERE email IN ('supervisor1@firm.com', 'supervisor2@firm.com'));
```

## API Impact

### Endpoints Affected
- `/api/v1/emergency/*` - Updated role checks
- `/api/v1/prank-detection/*` - Updated role requirements
- `/api/v1/personnel/*` - Updated validation rules
- `/api/v1/security-firms/*` - Updated validation rules

### Breaking Changes
- **Prank Detection Administrative Functions**: Now require `firm_supervisor` role instead of `office_staff`
- **User Type Validation**: API now accepts `firm_user` and `firm_supervisor` instead of `office_staff`
- **Emergency Providers System**: Now has role-based access control

### Emergency Providers System Permissions
- **Read Operations** (List, Get, Search): `firm_user`, `firm_supervisor`, `firm_admin`, `team_leader`, `field_agent`, `admin`, `super_admin`
- **CRUD Operations** (Create, Update, Delete): `firm_user`, `firm_supervisor`, `firm_admin`
- **Delete Unused Providers**: `firm_user`, `firm_supervisor`, `firm_admin`

## Backward Compatibility
- Existing `office_staff` records are automatically migrated to `firm_user`
- All existing permissions are preserved
- No API endpoint URLs have changed
- Only role names and permission requirements have been updated

## Testing
After applying the migration:

1. **Verify Role Updates**:
   ```sql
   SELECT role, COUNT(*) FROM firm_personnel GROUP BY role;
   SELECT role, COUNT(*) FROM firm_users GROUP BY role;
   ```

2. **Test API Endpoints**:
   - Emergency request allocation with `firm_user` role
   - Prank detection functions with `firm_supervisor` role
   - Personnel creation with new role types

3. **Verify Permissions**:
   - `firm_user` can perform basic operations
   - `firm_supervisor` can perform administrative operations
   - No unauthorized access to elevated functions

## Future Considerations
- Consider adding role-based UI elements to distinguish between `firm_user` and `firm_supervisor` capabilities
- May want to add additional granular permissions within roles
- Consider adding role transition workflows for promoting users