# User Model Documentation

## Overview

The DeltaCrown User model extends Django's `AbstractUser` with additional fields for tournament platform functionality.

## Key Features

### 1. **UUID Support**
- Added `uuid` field as unique identifier
- Currently uses `BigAutoField` as primary key for backward compatibility
- In fresh installations, UUID can be set as primary key

### 2. **Email Authentication**
- Email is unique and required
- Used as primary authentication method
- Email verification system with `is_verified` flag

### 3. **User Roles**
Three distinct roles with specific permissions:
- **PLAYER**: Default role for tournament participants
- **ORGANIZER**: Can create and manage tournaments
- **ADMIN**: Full system access

### 4. **Extended Profile Fields**
- `phone_number`: Contact information
- `date_of_birth`: Used for age verification
- `country`: Geographic information
- `avatar`: Profile picture (stored in `media/avatars/`)
- `bio`: User biography (max 500 characters)

## Model Structure

```python
class User(AbstractUser):
    # Identifiers
    id = BigAutoField (primary key)
    uuid = UUIDField (unique, for future migration)
    username = CharField (unique)
    email = EmailField (unique, required)
    
    # Authentication
    password = CharField (hashed)
    is_verified = BooleanField
    email_verified_at = DateTimeField
    
    # Role
    role = CharField (PLAYER/ORGANIZER/ADMIN)
    
    # Profile
    first_name = CharField
    last_name = CharField
    phone_number = CharField
    date_of_birth = DateField
    country = CharField
    avatar = ImageField
    bio = TextField
    
    # Permissions
    is_active = BooleanField
    is_staff = BooleanField
    is_superuser = BooleanField
    
    # Timestamps
    date_joined = DateTimeField
    last_login = DateTimeField
```

## Manager Methods

### `UserManager`
- `create_user(username, email, password)`: Create regular user
- `create_superuser(username, email, password)`: Create admin user with verified email

## Properties

```python
# Role checks
user.is_player          # Returns True if role == PLAYER
user.is_organizer       # Returns True if role == ORGANIZER
user.is_admin_role      # Returns True if role == ADMIN

# Utility properties
user.full_name          # Returns "First Last" or username
user.age                # Calculated from date_of_birth
```

## Admin Interface

Enhanced Django admin with:
- List display: username, email, role, verification status, join date
- Filters: role, verification, active status, staff status
- Search: username, email, name, phone
- Readonly fields: id, uuid, timestamps
- Organized fieldsets:
  - Identity (id, uuid, username, password)
  - Personal Info (name, email, phone, DOB, country)
  - Profile (avatar, bio)
  - Role & Permissions
  - Important Dates

## Database Indexes

Performance indexes on:
- `email` (for authentication lookups)
- `role` (for role-based queries)
- `is_verified` (for filtering verified users)

## Usage Examples

### Create User
```python
from apps.accounts.models import User

# Create player
user = User.objects.create_user(
    username='player1',
    email='player@example.com',
    password='secure_password',
    first_name='John',
    last_name='Doe',
    role=User.Role.PLAYER
)

# Create organizer
organizer = User.objects.create_user(
    username='org1',
    email='org@example.com',
    password='secure_password',
    role=User.Role.ORGANIZER
)
```

### Check Role
```python
if user.is_player:
    # Player-specific logic
    pass

if user.is_organizer:
    # Organizer-specific logic
    pass
```

### Update Profile
```python
user.phone_number = '+8801234567890'
user.country = 'Bangladesh'
user.bio = 'Professional esports player'
user.save()
```

### Verify Email
```python
user.mark_email_verified()
# Sets is_verified=True, email_verified_at=now(), is_active=True
```

## Migration Path

### Current State (0006_user_extended_fields)
- ✅ Role field added
- ✅ Extended profile fields added
- ✅ UUID field added as unique
- ✅ Indexes created
- ⚠️ Primary key still BigAutoField

### Future Migration (Fresh Installations)
For new installations, change primary key to UUID:
```python
id = models.UUIDField(
    primary_key=True,
    default=uuid.uuid4,
    editable=False
)
```

### Existing Database Considerations
Converting existing BigAutoField to UUID requires:
1. Data migration to populate UUID for existing users
2. Update all foreign key references
3. Switch primary key
4. Complex rollback procedure

**Recommendation**: Keep BigAutoField for existing databases, use UUID for new installations.

## Related Models

- `EmailOTP`: Email verification codes
- `PendingSignup`: Temporary signup records
- `UserProfile`: Additional profile information (if exists)
- `Team`: Team memberships
- `Tournament`: Tournament registrations

## Security Considerations

1. **Email Verification**: Required before full account activation
2. **Password Hashing**: Django's PBKDF2 by default
3. **Role-Based Access**: Enforced at view/API level
4. **UUID**: Prevents ID enumeration attacks (when used as primary key)

## API Endpoints

See BE-005 documentation for JWT authentication endpoints:
- POST `/api/auth/register/` - User registration
- POST `/api/auth/login/` - Login with email/username
- GET `/api/auth/me/` - Get authenticated user details
- PATCH `/api/auth/me/` - Update user profile

## Testing

```python
from apps.accounts.models import User

def test_user_creation():
    user = User.objects.create_user(
        username='test',
        email='test@example.com',
        password='test123'
    )
    assert user.uuid is not None
    assert user.role == User.Role.PLAYER
    assert not user.is_verified

def test_email_verification():
    user = User.objects.create_user(
        username='test',
        email='test@example.com',
        password='test123'
    )
    user.mark_email_verified()
    assert user.is_verified
    assert user.email_verified_at is not None
```

## Configuration

### Settings Required
```python
# settings/base.py
AUTH_USER_MODEL = 'accounts.User'

# Media files for avatars
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Image processing (requires Pillow)
# pip install Pillow
```

## Dependencies

- `Pillow`: For avatar image processing
- `django-environ`: For environment configuration
- Standard Django auth system

## Troubleshooting

### Issue: Migration fails with existing users
**Solution**: Run migrations incrementally, test on staging first

### Issue: UUID not populated for existing users
**Solution**: Create data migration to backfill UUID values

### Issue: Avatar upload fails
**Solution**: Check MEDIA_ROOT permissions and Pillow installation

## Future Enhancements

1. Make UUID the primary key (requires major migration)
2. Add social authentication fields
3. Add two-factor authentication support
4. Add user preferences/settings JSON field
5. Add last activity timestamp
6. Add account suspension/ban functionality

---

**Last Updated**: November 4, 2025
**Migration**: 0006_user_extended_fields
**Status**: ✅ Complete (BE-004)
