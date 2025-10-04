# User Group Memberships System

## Overview

The User Group Memberships system implements a proper many-to-many relationship between users and groups, eliminating redundancy in the user_groups table. This design allows multiple users to belong to the same group and users to belong to multiple groups.

## Database Schema Changes

### Previous Structure
```sql
-- Old user_groups table (with redundancy)
user_groups:
  - id (UUID, PK)
  - user_id (UUID, FK to registered_users) ❌ REMOVED
  - name
  - address
  - location
  - subscription_id
  - subscription_expires_at
  - created_at
  - updated_at
```

### New Structure
```sql
-- Refactored user_groups table (no user_id)
user_groups:
  - id (UUID, PK)
  - name
  - address
  - location
  - subscription_id
  - subscription_expires_at
  - created_at
  - updated_at

-- New junction table for many-to-many relationships
user_group_memberships:
  - id (UUID, PK)
  - user_id (UUID, FK to registered_users)
  - group_id (UUID, FK to user_groups)
  - role (VARCHAR, member|admin|owner)
  - joined_at (TIMESTAMP)
  - is_active (BOOLEAN)
  - created_at (TIMESTAMP)
  - updated_at (TIMESTAMP)
  - UNIQUE(user_id, group_id)
```

## Model Relationships

### UserGroupMembership Model
```python
class UserGroupMembership(BaseModel):
    __tablename__ = "user_group_memberships"
    
    user_id = Column(UUID, ForeignKey("registered_users.id"), nullable=False)
    group_id = Column(UUID, ForeignKey("user_groups.id"), nullable=False)
    role = Column(String(20), default="member", nullable=False)
    joined_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    user = relationship("RegisteredUser", back_populates="group_memberships")
    group = relationship("UserGroup", back_populates="memberships")
    
    __table_args__ = (
        UniqueConstraint("user_id", "group_id", name="uq_user_group_membership"),
    )
```

### Updated RegisteredUser Model
```python
class RegisteredUser(BaseModel):
    # ... other fields ...
    
    # OLD: groups = relationship("UserGroup", back_populates="user", cascade="all, delete-orphan")
    # NEW:
    group_memberships = relationship("UserGroupMembership", back_populates="user", cascade="all, delete-orphan")
```

### Updated UserGroup Model
```python
class UserGroup(BaseModel):
    # user_id field REMOVED
    
    # Relationships
    memberships = relationship("UserGroupMembership", back_populates="group", cascade="all, delete-orphan")
    mobile_numbers = relationship("GroupMobileNumber", back_populates="group", cascade="all, delete-orphan")
    panic_requests = relationship("PanicRequest", back_populates="group")
```

## Role-Based Access Control

### Roles
- **owner**: Full control over the group, can add/remove members, change settings, transfer ownership
- **admin**: Can add/remove regular members, cannot remove owners or other admins
- **member**: Basic access to group features, no management permissions

### Role Hierarchy
```
owner > admin > member
```

## Service Layer

### UserGroupMembershipService

Key methods for managing group memberships:

#### Core Operations
```python
# Add user to group
await service.add_user_to_group(user_id, group_id, role="member")

# Remove user from group (soft delete)
await service.remove_user_from_group(user_id, group_id)

# Check membership
is_member = await service.is_user_member_of_group(user_id, group_id)
```

#### Querying
```python
# Get user's groups
groups = await service.get_user_groups(user_id, active_only=True)

# Get group members with roles
members = await service.get_group_members(group_id, active_only=True)

# Get owners/admins
owners = await service.get_group_owners(group_id)
admins = await service.get_group_admins(group_id)
```

#### Role Management
```python
# Update role
await service.update_membership_role(user_id, group_id, "admin")

# Transfer ownership
await service.transfer_group_ownership(group_id, current_owner_id, new_owner_id)
```

## Migration Process

### Data Migration Steps

1. **Create new junction table**:
```sql
CREATE TABLE user_group_memberships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES registered_users(id),
    group_id UUID NOT NULL REFERENCES user_groups(id),
    role VARCHAR(20) NOT NULL DEFAULT 'member',
    joined_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    CONSTRAINT uq_user_group_membership UNIQUE (user_id, group_id)
);
```

2. **Migrate existing data**:
```sql
INSERT INTO user_group_memberships (user_id, group_id, role, joined_at, is_active)
SELECT 
    user_id,
    id as group_id,
    'owner' as role,  -- Original user becomes owner
    created_at as joined_at,
    true as is_active
FROM user_groups;
```

3. **Remove user_id from user_groups**:
```sql
ALTER TABLE user_groups DROP CONSTRAINT user_groups_user_id_fkey;
ALTER TABLE user_groups DROP COLUMN user_id;
```

### Verification Queries
```sql
-- Verify data migration
SELECT COUNT(*) as migrated_memberships FROM user_group_memberships;
SELECT COUNT(*) as original_groups FROM user_groups;

-- Check for any orphaned data
SELECT * FROM user_group_memberships 
WHERE user_id NOT IN (SELECT id FROM registered_users);

SELECT * FROM user_group_memberships 
WHERE group_id NOT IN (SELECT id FROM user_groups);
```

## Benefits of the New Structure

### Eliminated Redundancy
- **Before**: Each group could only have one user (1:1 relationship)
- **After**: Multiple users can belong to the same group (M:N relationship)

### Improved Flexibility
- Users can join multiple groups
- Groups can have multiple members with different roles
- Easier to implement features like:
  - Group sharing among family members
  - Business accounts with multiple employees
  - Emergency contact groups

### Better Data Integrity
- Proper foreign key constraints
- Unique constraints prevent duplicate memberships
- Soft delete capability (is_active flag)

## Usage Examples

### Creating a Family Group
```python
# Create a new group
group = UserGroup(
    name="Smith Family",
    address="123 Main St, Anytown, USA",
    location=from_shape(Point(-74.0060, 40.7128), srid=4326)
)

# Add family members
membership_service = UserGroupMembershipService(db)

# John as owner (group creator)
await membership_service.add_user_to_group(john_id, group.id, "owner")

# Jane as admin
await membership_service.add_user_to_group(jane_id, group.id, "admin")

# Kids as members
await membership_service.add_user_to_group(kid1_id, group.id, "member")
await membership_service.add_user_to_group(kid2_id, group.id, "member")
```

### Business Use Case
```python
# Security company with multiple employees
company_group = UserGroup(
    name="SecureGuard Services",
    address="456 Business Ave, Metro City",
    location=from_shape(Point(-73.9857, 40.7484), srid=4326)
)

# Add employees with appropriate roles
await membership_service.add_user_to_group(manager_id, company_group.id, "owner")
await membership_service.add_user_to_group(supervisor_id, company_group.id, "admin")
await membership_service.add_user_to_group(guard1_id, company_group.id, "member")
await membership_service.add_user_to_group(guard2_id, company_group.id, "member")
```

### Querying Group Data
```python
# Get all members of a group with their roles
members = await membership_service.get_group_members(group_id)
for user, membership in members:
    print(f"{user.first_name} {user.last_name} - Role: {membership.role}")

# Get all groups a user belongs to
user_groups = await membership_service.get_user_groups(user_id)
for group in user_groups:
    print(f"Member of: {group.name}")

# Check if user can manage group
owners = await membership_service.get_group_owners(group_id)
admins = await membership_service.get_group_admins(group_id)
can_manage = user_id in [u.id for u in owners + admins]
```

## API Impact

### Updated Endpoints

APIs that previously assumed 1:1 user-group relationships need updates:

#### Group Management
```python
# Before: user_group.user_id
# After: Multiple users via memberships

async def get_group_info(group_id: UUID):
    group = await get_group(group_id)
    members = await membership_service.get_group_members(group_id)
    return {
        "group": group,
        "members": [
            {
                "user": user,
                "role": membership.role,
                "joined_at": membership.joined_at
            } 
            for user, membership in members
        ]
    }
```

#### User Dashboard
```python
# Before: user.groups (direct relationship)
# After: Via membership service

async def get_user_dashboard(user_id: UUID):
    groups = await membership_service.get_user_groups(user_id)
    return {
        "user_groups": [
            {
                "group": group,
                "role": await get_user_role_in_group(user_id, group.id)
            }
            for group in groups
        ]
    }
```

## Performance Considerations

### Indexing Strategy
```sql
-- Performance indexes on junction table
CREATE INDEX idx_user_group_memberships_user_id ON user_group_memberships(user_id);
CREATE INDEX idx_user_group_memberships_group_id ON user_group_memberships(group_id);
CREATE INDEX idx_user_group_memberships_role ON user_group_memberships(role);
CREATE INDEX idx_user_group_memberships_is_active ON user_group_memberships(is_active);
```

### Query Optimization
- Use `selectinload()` for eager loading relationships
- Consider caching frequently accessed membership data
- Use composite indexes for complex queries

### Memory Usage
- Junction table adds minimal overhead
- Eliminates data duplication in user_groups
- Better normalization reduces storage requirements

## Security Considerations

### Access Control
- Always verify user permissions before membership operations
- Implement proper role-based authorization
- Log membership changes for audit trails

### Data Protection
- Soft delete preserves audit trail
- Foreign key constraints ensure data integrity
- Unique constraints prevent duplicate memberships

## Testing

### Unit Tests
```python
async def test_add_user_to_group():
    service = UserGroupMembershipService(db)
    
    # Test successful addition
    membership = await service.add_user_to_group(user_id, group_id, "member")
    assert membership.role == "member"
    assert membership.is_active == True
    
    # Test duplicate prevention
    with pytest.raises(ValueError):
        await service.add_user_to_group(user_id, group_id, "admin")

async def test_role_hierarchy():
    service = UserGroupMembershipService(db)
    
    # Add users with different roles
    await service.add_user_to_group(owner_id, group_id, "owner")
    await service.add_user_to_group(admin_id, group_id, "admin")
    await service.add_user_to_group(member_id, group_id, "member")
    
    # Verify role queries
    owners = await service.get_group_owners(group_id)
    admins = await service.get_group_admins(group_id)
    
    assert len(owners) == 1
    assert len(admins) == 2  # owner + admin
```

### Integration Tests
```python
async def test_group_membership_workflow():
    # Create group and users
    group = await create_test_group()
    user1, user2 = await create_test_users(2)
    
    service = UserGroupMembershipService(db)
    
    # Add users to group
    await service.add_user_to_group(user1.id, group.id, "owner")
    await service.add_user_to_group(user2.id, group.id, "member")
    
    # Verify memberships
    user1_groups = await service.get_user_groups(user1.id)
    user2_groups = await service.get_user_groups(user2.id)
    
    assert group.id in [g.id for g in user1_groups]
    assert group.id in [g.id for g in user2_groups]
    
    # Test role update
    await service.update_membership_role(user2.id, group.id, "admin")
    
    # Verify role change
    admins = await service.get_group_admins(group.id)
    assert user2.id in [u.id for u in admins]
```

## Future Enhancements

### Planned Features
- **Group Invitations**: Send invites to join groups
- **Membership Requests**: Users can request to join private groups
- **Group Templates**: Create groups from predefined templates
- **Bulk Operations**: Add/remove multiple users at once
- **Group Hierarchies**: Support for parent/child group relationships

### Advanced Role Management
- **Custom Roles**: Define custom roles beyond owner/admin/member
- **Permissions Matrix**: Granular permissions for different actions
- **Time-Limited Memberships**: Automatic role expiration
- **Role Inheritance**: Inherit roles from parent groups

## Troubleshooting

### Common Issues

#### Missing Memberships After Migration
```sql
-- Check for users without any group memberships
SELECT u.id, u.email 
FROM registered_users u
LEFT JOIN user_group_memberships ugm ON u.id = ugm.user_id
WHERE ugm.user_id IS NULL;
```

#### Orphaned Groups
```sql
-- Check for groups with no active members
SELECT g.id, g.name
FROM user_groups g
LEFT JOIN user_group_memberships ugm ON g.id = ugm.group_id AND ugm.is_active = true
WHERE ugm.group_id IS NULL;
```

#### Multiple Owners
```sql
-- Check for groups with multiple owners (should be rare)
SELECT group_id, COUNT(*) as owner_count
FROM user_group_memberships
WHERE role = 'owner' AND is_active = true
GROUP BY group_id
HAVING COUNT(*) > 1;
```

### Performance Issues
- Monitor query performance on junction table joins
- Consider denormalizing frequently accessed data
- Use appropriate indexes for common query patterns
- Implement caching for membership checks

## Implementation Status

- ✅ Database schema updated
- ✅ Models refactored with proper relationships
- ✅ Junction table created with indexes
- ✅ Data migration completed
- ✅ Service layer implemented
- ✅ Role-based access control
- ✅ Comprehensive documentation
- ⏳ API endpoints update pending
- ⏳ Frontend integration pending
- ⏳ Comprehensive testing pending