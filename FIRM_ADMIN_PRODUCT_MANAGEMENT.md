# Firm Admin Product Management Implementation

## Overview

This implementation provides comprehensive CRUD (Create, Read, Update, Delete) operations for subscription products that firm administrators can manage for their own security firms. The system ensures proper authorization and prevents deletion of products that have been used in the system.

## Key Features

### 1. **Authorization & Security**
- Only users with `firm_admin` role can access product management endpoints
- Firm admins can only manage products belonging to their own firm
- All operations are properly authenticated and authorized
- Automatic firm_id assignment based on authenticated user's firm

### 2. **CRUD Operations**

#### **Create Product** (`POST /api/v1/subscription-products/`)
- Creates a new subscription product for the firm admin's firm
- Automatically uses the authenticated user's firm_id
- Validates input parameters (price, max_users, credit_cost)
- Deducts credits from firm balance upon successful creation
- Requires sufficient firm credits to create the product

**Request Body:**
```json
{
  "name": "Premium Security Package",
  "description": "24/7 monitoring with rapid response team",
  "max_users": 10,
  "price": 299.99,
  "credit_cost": 50
}
```

#### **Read Operations**

**Get My Products** (`GET /api/v1/subscription-products/my-products`)
- Retrieves all products for the current firm admin's firm
- Optional parameter: `include_inactive=true` to include inactive products
- Returns paginated list with total count
- Returns empty list `{"products": [], "total_count": 0}` if no products exist

**Get Specific Product** (`GET /api/v1/subscription-products/{product_id}`)
- Retrieves detailed information about a specific product
- Only allows access to products from the firm admin's own firm
- Returns complete product details including pricing and status

#### **Update Product** (`PUT /api/v1/subscription-products/{product_id}`)
- Updates existing product information
- Only allows updates to products from the firm admin's own firm
- Supports partial updates (only provided fields are updated)
- Can update: name, description, max_users, price, is_active status

**Request Body (all fields optional):**
```json
{
  "name": "Updated Product Name",
  "description": "Updated description",
  "max_users": 15,
  "price": 399.99,
  "is_active": false
}
```

#### **Delete Product** (`DELETE /api/v1/subscription-products/{product_id}`)
- Permanently deletes a subscription product
- **Critical Restriction**: Only allows deletion if the product has NEVER been used
- Checks for any existing subscriptions (purchased or applied)
- Only allows deletion of products from the firm admin's own firm
- Provides detailed error message if deletion is not allowed

### 3. **Business Rules**

#### **Product Creation Rules**
- Firm must be approved (`verification_status = "approved"`)
- Firm must have sufficient credits to cover creation cost
- Maximum users must be greater than 0
- Price cannot be negative
- Credit cost must be greater than 0

#### **Product Deletion Rules**
- Product can only be deleted if it has NEVER been purchased/used
- System checks for any `StoredSubscription` records linked to the product
- If any subscriptions exist (even if not applied), deletion is prevented
- This ensures data integrity and prevents orphaned subscription records

#### **Authorization Rules**
- All endpoints require `firm_admin` role
- Firm admins can only access products from their own firm
- Cross-firm access is strictly prohibited
- Automatic firm_id validation on all operations

### 4. **Additional Features**

#### **Product Statistics** (`GET /api/v1/subscription-products/{product_id}/statistics`)
- Provides detailed analytics for a specific product
- Shows total purchases, applied subscriptions, revenue, etc.
- Only accessible for products from the firm admin's own firm

#### **Public Product Listing** (`GET /api/v1/subscription-products/`)
- Lists all active products from all firms (for customer browsing)
- No firm admin restriction (public endpoint)
- Used by registered users to browse available subscription options
- Returns empty list `{"products": [], "total_count": 0}` if no active products exist

## API Endpoints Summary

| Method | Endpoint | Description | Authorization |
|--------|----------|-------------|---------------|
| POST | `/subscription-products/` | Create new product | Firm Admin |
| GET | `/subscription-products/my-products` | Get firm's products | Firm Admin |
| GET | `/subscription-products/{id}` | Get specific product | Firm Admin |
| PUT | `/subscription-products/{id}` | Update product | Firm Admin |
| DELETE | `/subscription-products/{id}` | Delete unused product | Firm Admin |
| GET | `/subscription-products/{id}/statistics` | Get product stats | Firm Admin |
| GET | `/subscription-products/` | List active products | Any User |

## Error Handling

### Common Error Responses

**403 Forbidden - Cross-firm access:**
```json
{
  "detail": "You can only manage products from your own firm"
}
```

**400 Bad Request - Product has subscriptions:**
```json
{
  "detail": "Cannot delete product that has been used in the system. This product has 5 subscription(s) associated with it."
}
```

**402 Payment Required - Insufficient credits:**
```json
{
  "detail": "Insufficient credits. Current balance: 25, Required: 50"
}
```

## Testing

A comprehensive test script (`test_firm_admin_products.py`) is provided that demonstrates:
- Authentication as firm admin
- Creating products
- Reading product lists and individual products
- Updating product information
- Attempting to delete products
- Handling various error scenarios

## Database Schema

The implementation uses existing models:
- `SubscriptionProduct` - Main product table
- `StoredSubscription` - Tracks product usage
- `SecurityFirm` - Firm information and credit balance
- `FirmUser` - Links users to firms with roles

## Security Considerations

1. **Role-based Access Control**: Only firm admins can access these endpoints
2. **Firm Isolation**: Strict enforcement of firm boundaries
3. **Data Integrity**: Prevents deletion of products with existing subscriptions
4. **Credit Management**: Automatic credit deduction with validation
5. **Input Validation**: Comprehensive validation of all input parameters

## Usage Example

```python
# Create a product
product_data = {
    "name": "Premium Security Package",
    "description": "24/7 monitoring service",
    "max_users": 10,
    "price": 299.99,
    "credit_cost": 50
}

# Update a product
update_data = {
    "price": 349.99,
    "is_active": False
}

# The system automatically handles firm_id assignment and authorization
```

This implementation provides a secure, comprehensive solution for firm administrators to manage their subscription products while maintaining strict data integrity and authorization controls.