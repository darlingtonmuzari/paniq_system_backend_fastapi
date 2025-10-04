# Emergency Role Permissions Update

## Summary

Updated the emergency API endpoints to allow the following roles to **Read** and **Update** panic requests:
- `firm_user` - can allocate requests to teams or service providers
- `firm_supervisor` - can allocate requests and handle call services  
- `team_leader` - can allocate and reassign requests

## Changes Made

### 1. `/agent/requests` endpoint
- **Updated roles allowed**: `field_agent`, `team_leader`, `firm_user`, `firm_supervisor`
- **Previous**: Only `field_agent` and `team_leader`
- **Action**: Added `firm_user` and `firm_supervisor` to allowed roles

### 2. `/dashboard/agent/requests` endpoint
- **Updated roles allowed**: `field_agent`, `team_leader`, `firm_user`, `firm_supervisor`
- **Previous**: Only `field_agent` and `team_leader`
- **Action**: Added `firm_user` and `firm_supervisor` to allowed roles

### 3. `/requests/{request_id}/status` endpoint (PUT)
- **Updated roles allowed**: `field_agent`, `team_leader`, `firm_user`, `firm_supervisor`
- **Previous**: No explicit role restrictions (only authentication required)
- **Action**: Added proper role-based authorization with the specified roles

### 4. Documentation Updates
- Updated endpoint docstrings to reflect the new role permissions
- Updated `/teams/{team_id}/requests` and `/firm/{firm_id}/pending` endpoint descriptions to clarify that all firm personnel can access them

## Existing Endpoints Already Supporting These Roles

The following endpoints already allowed all firm personnel (including the specified roles) without additional changes needed:

1. **`/firm/{firm_id}/pending`** - Get pending requests for firm
2. **`/teams/{team_id}/requests`** - Get team-assigned requests  
3. **`/requests/{request_id}/allocate`** - Allocate requests (already allowed these roles)
4. **`/requests/{request_id}/handle-call`** - Handle call services (already allowed firm_user and firm_supervisor)
5. **`/requests/{request_id}/reassign`** - Reassign requests (already allowed these roles)

## Role Capabilities Matrix

| Role | Read Requests | Update Status | Allocate | Handle Calls | Reassign |
|------|---------------|---------------|----------|--------------|----------|
| `firm_user` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `firm_supervisor` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `team_leader` | ✅ | ✅ | ✅ | ❌ | ✅ |
| `field_agent` | ✅ | ✅ | ❌ | ❌ | ❌ |

## Testing

Created and ran `test_role_permissions_emergency.py` which confirmed:
- ✅ All specified roles can access the updated endpoints
- ✅ Invalid roles are properly denied with 403 errors
- ✅ Clear error messages indicate which roles are allowed
- ✅ No syntax errors in the updated code

## Files Modified

1. **`app/api/v1/emergency.py`** - Main emergency API endpoints
2. **`test_role_permissions_emergency.py`** - Test script (new file)
3. **`EMERGENCY_ROLE_PERMISSIONS_UPDATE.md`** - This documentation (new file)

## Impact

These changes enable firm users, firm supervisors, and team leaders to:
1. **Read panic requests** from multiple endpoints
2. **Update request status** with location tracking
3. **Maintain existing allocation/reassignment capabilities**

The updates maintain security by:
- Requiring firm personnel status
- Restricting access to specific roles
- Preserving existing business logic and permissions