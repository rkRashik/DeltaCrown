# Email Verification System - Implementation Guide

## Overview

Modern minimalist email verification system with OTP (One-Time Password) for public email addresses. Users can choose to use their primary account email or add a separate custom email for public display.

**Implementation Date**: 2026-01-08

---

## Features

### ✨ Key Features

1. **Dual Email Options**
   - Use primary account email as public email (verified instantly)
   - Add custom secondary email for public display (requires OTP verification)
   - Toggle between options with modern card-based UI

2. **OTP Verification**
   - 6-digit numeric code sent via email
   - 10-minute expiration time
   - Rate limiting (3 attempts per hour)
   - Auto-focus and keyboard navigation
   - Paste support for quick entry

3. **Modern UI/UX**
   - Gradient card design with glassmorphism
   - Real-time status indicators (verified, unverified, pending)
   - Smooth animations and transitions
   - Responsive mobile-friendly layout
   - Accessible keyboard controls

4. **Security**
   - Rate limiting prevents brute force
   - OTP stored in cache (not database)
   - Auto-expires after 10 minutes
   - CSRF protection
   - Email format validation

---

## Architecture

### Backend Components

**File**: `apps/user_profile/views/email_verification_api.py`

#### 1. `send_verification_otp(request)`
- **Method**: POST
- **URL**: `/me/settings/send-verification-otp/`
- **Payload**:
  ```json
  {
    "email": "user@example.com",
    "use_primary": false
  }
  ```
- **Response**:
  ```json
  {
    "success": true,
    "message": "Verification code sent to user@example.com",
    "expires_in": 600
  }
  ```
- **Rate Limit**: 3 attempts per hour per user
- **Cache**: Stores OTP for 10 minutes

#### 2. `verify_otp_code(request)`
- **Method**: POST
- **URL**: `/me/settings/verify-otp-code/`
- **Payload**:
  ```json
  {
    "email": "user@example.com",
    "code": "123456",
    "use_primary": false
  }
  ```
- **Response**:
  ```json
  {
    "success": true,
    "message": "Email verified successfully!",
    "email": "user@example.com",
    "verified": true
  }
  ```
- **Action**: Updates `UserProfile.secondary_email` and `secondary_email_verified`

### Frontend Components

**File**: `templates/user_profile/profile/settings_control_deck.html`

#### Key UI Elements

1. **Email Source Toggle**
   ```html
   <button onclick="toggleEmailSource('primary')">Use Primary Email</button>
   <button onclick="toggleEmailSource('custom')">Custom Email</button>
   ```

2. **OTP Input Grid**
   ```html
   <input class="otp-digit" maxlength="1" data-index="0">
   <!-- 6 inputs total -->
   ```

3. **Verification Status**
   - ✅ Verified: Green badge with shield icon
   - ⚠️ Unverified: Amber warning with "Verify Now" button
   - 🔒 Primary: Blue badge showing account email

#### JavaScript Functions

| Function | Purpose |
|----------|---------|
| `toggleEmailSource(source)` | Switch between primary/custom email |
| `startEmailVerification()` | Initiate OTP sending process |
| `showOtpPanel(email)` | Display OTP input interface |
| `setupOtpInputs()` | Configure keyboard navigation |
| `verifyOtpCode()` | Submit OTP for verification |
| `cancelOtpVerification()` | Close OTP panel |
| `resendOtpCode()` | Request new OTP code |
| `changeVerifiedEmail()` | Reset verified email |

---

## Database Schema

### UserProfile Model
```python
class UserProfile(models.Model):
    # ... existing fields ...
    
    # Email fields (added 2026-01-08)
    secondary_email = models.EmailField(blank=True, default="")
    secondary_email_verified = models.BooleanField(default=False)
```

**Migration**: `0054_userprofile_preferred_contact_method_and_more.py`

---

## Cache Keys

### OTP Storage
```python
# Key format: email_otp_{user_id}_{email}
# Example: email_otp_42_user@example.com
# TTL: 600 seconds (10 minutes)
cache.set('email_otp_42_user@example.com', '123456', timeout=600)
```

### Rate Limiting
```python
# Key format: email_otp_attempts_{user_id}
# Example: email_otp_attempts_42
# TTL: 3600 seconds (1 hour)
# Max value: 3
cache.set('email_otp_attempts_42', 2, timeout=3600)
```

---

## User Flow

### Flow 1: Use Primary Email

```
1. User clicks "Use Primary Email" tab
   └─> Shows account email in locked display

2. User clicks "Verify Email Now"
   └─> API: POST /send-verification-otp/ { email: account_email, use_primary: true }
   └─> Email sent with 6-digit code

3. User enters OTP code
   └─> API: POST /verify-otp-code/ { email: account_email, code: "123456", use_primary: true }
   
4. Success:
   └─> secondary_email = user.email
   └─> secondary_email_verified = True
   └─> UI shows green "Verified" badge
```

### Flow 2: Use Custom Email

```
1. User clicks "Custom Email" tab
   └─> Shows text input for email

2. User types custom email
   └─> Shows "Email not verified yet" warning

3. User clicks "Verify Email Now"
   └─> API: POST /send-verification-otp/ { email: custom_email, use_primary: false }
   └─> Email sent to custom address

4. User enters OTP code
   └─> API: POST /verify-otp-code/ { email: custom_email, code: "123456", use_primary: false }

5. Success:
   └─> secondary_email = custom_email
   └─> secondary_email_verified = True
   └─> UI shows green "Verified" badge
```

### Flow 3: Change Verified Email

```
1. User clicks "Change" button on verified email
   └─> Confirmation dialog appears

2. User confirms
   └─> UI resets to unverified state
   └─> secondary_email_verified = False (on save)
   └─> User can enter new email and verify
```

---

## Email Template

**Subject**: Verify Your Public Email - DeltaCrown

**Body**:
```
Hi {username},

Your verification code is: {OTP}

This code will expire in 10 minutes.

If you didn't request this verification, please ignore this email.

Best regards,
DeltaCrown Team
```

---

## Security Considerations

### Rate Limiting
- **3 attempts per hour** per user
- Prevents brute force attacks
- Counter resets on successful verification

### OTP Expiration
- **10 minutes** validity
- Stored in cache (Redis/Memcached)
- Auto-deleted on verification

### Validation
- Email format validation (RFC 5322)
- CSRF token required
- Login required decorator
- HTTP method restrictions (POST only)

### Cache vs Database
- ✅ OTP stored in cache (temporary)
- ✅ Verification status in database (permanent)
- ✅ No sensitive data in database

---

## Testing Checklist

### Backend Tests
- [ ] OTP generation (6 digits)
- [ ] Email sending (SMTP configured)
- [ ] Rate limiting (4th attempt blocked)
- [ ] OTP expiration (after 10 minutes)
- [ ] Invalid OTP rejection
- [ ] Valid OTP acceptance
- [ ] Database update on success

### Frontend Tests
- [ ] Toggle between primary/custom email
- [ ] Email input validation
- [ ] OTP panel display
- [ ] Keyboard navigation (arrows, backspace)
- [ ] Paste support (6-digit code)
- [ ] Success state update
- [ ] Error handling (shake animation)
- [ ] Resend OTP functionality
- [ ] Cancel verification

### Integration Tests
- [ ] End-to-end verification flow
- [ ] Multiple users simultaneously
- [ ] Rate limit across sessions
- [ ] Email delivery time
- [ ] Mobile responsiveness

---

## Configuration

### Django Settings

**Required**:
```python
# Email backend (production)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@gmail.com'
EMAIL_HOST_PASSWORD = 'your-app-password'
DEFAULT_FROM_EMAIL = 'noreply@deltacrown.com'
```

**Development** (console output):
```python
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
```

### Cache Configuration

**Required**: Redis or Memcached for OTP storage

```python
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
    }
}
```

---

## Admin Panel

### Viewing Verification Status

**URL**: http://127.0.0.1:8000/admin/user_profile/userprofile/

**Fields** (Contact Information section):
- `secondary_email`: Editable by admin
- `secondary_email_verified`: **Read-only** (only system can verify via OTP)

**Note**: Admins can manually set email but cannot mark as verified. This ensures verification integrity.

---

## Troubleshooting

### Issue: "Email not sending"

**Causes**:
1. SMTP settings not configured
2. Firewall blocking port 587
3. Invalid email credentials
4. Rate limit exceeded

**Solutions**:
1. Check `settings.py` EMAIL_* configuration
2. Use `EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'` for testing
3. Verify email provider allows SMTP access
4. Wait 1 hour if rate limited

### Issue: "OTP expired"

**Causes**:
- 10 minutes passed since sending
- Cache cleared/restarted

**Solutions**:
- Click "Resend" to get new code
- Check cache backend is running (Redis/Memcached)

### Issue: "Invalid verification code"

**Causes**:
- Wrong code entered
- Code expired
- Case sensitivity (shouldn't happen with numbers)

**Solutions**:
- Double-check email for correct code
- Request new code if expired
- Copy-paste code to avoid typos

### Issue: "Too many attempts"

**Causes**:
- 3+ verification requests in 1 hour

**Solutions**:
- Wait 1 hour for counter reset
- Contact admin to clear cache manually:
  ```python
  from django.core.cache import cache
  cache.delete('email_otp_attempts_{user_id}')
  ```

---

## Future Enhancements

### Planned Features
- [ ] SMS verification as alternative
- [ ] Email change history log
- [ ] Verification badge on public profile
- [ ] Admin dashboard for verification stats
- [ ] Custom email templates (HTML)
- [ ] Multi-language support
- [ ] QR code verification
- [ ] Biometric verification (mobile)

### Performance Optimizations
- [ ] Async email sending (Celery)
- [ ] CDN for static assets
- [ ] WebSocket for real-time updates
- [ ] Progressive Web App (PWA) support

---

## API Reference

### POST /me/settings/send-verification-otp/

**Request**:
```json
{
  "email": "user@example.com",
  "use_primary": false
}
```

**Success Response** (200):
```json
{
  "success": true,
  "message": "Verification code sent to user@example.com",
  "expires_in": 600
}
```

**Error Responses**:

**400 Bad Request**:
```json
{
  "success": false,
  "error": "Invalid email address"
}
```

**429 Too Many Requests**:
```json
{
  "success": false,
  "error": "Too many verification attempts. Please try again in 1 hour."
}
```

**500 Internal Server Error**:
```json
{
  "success": false,
  "error": "Failed to send verification email. Please try again later."
}
```

---

### POST /me/settings/verify-otp-code/

**Request**:
```json
{
  "email": "user@example.com",
  "code": "123456",
  "use_primary": false
}
```

**Success Response** (200):
```json
{
  "success": true,
  "message": "Email verified successfully!",
  "email": "user@example.com",
  "verified": true
}
```

**Error Responses**:

**400 Bad Request** (expired):
```json
{
  "success": false,
  "error": "Verification code expired or not found. Please request a new code."
}
```

**400 Bad Request** (invalid):
```json
{
  "success": false,
  "error": "Invalid verification code"
}
```

---

## Developer Notes

### Adding New Verification Methods

To add SMS, phone, or other verification methods:

1. **Create new API file**:
   ```python
   # apps/user_profile/views/sms_verification_api.py
   ```

2. **Add URL patterns**:
   ```python
   path("me/settings/send-sms-otp/", send_sms_otp, name="send_sms_otp"),
   ```

3. **Update frontend**:
   - Add new tab in email verification section
   - Create similar OTP input interface
   - Update JavaScript to handle SMS flow

4. **Update model** (if needed):
   ```python
   phone_verified = models.BooleanField(default=False)
   ```

### Extending Rate Limits

To customize rate limiting:

```python
# In email_verification_api.py

# Change attempts per hour
MAX_ATTEMPTS = 5  # Default: 3

# Change time window
ATTEMPT_WINDOW = 7200  # 2 hours (default: 3600)

# Per-email rate limiting (not per-user)
attempt_key = f"email_otp_attempts_{email}"
```

---

## Changelog

### Version 1.0 (2026-01-08)
- ✅ Initial implementation
- ✅ OTP verification via email
- ✅ Primary/custom email toggle
- ✅ Modern minimalist UI
- ✅ Rate limiting (3/hour)
- ✅ 10-minute OTP expiration
- ✅ Keyboard navigation
- ✅ Paste support
- ✅ Admin panel integration
- ✅ CSRF protection
- ✅ Mobile responsive

---

## Support

For issues or questions:
- Check troubleshooting section above
- Review [ADMIN_ORGANIZATION.md](ADMIN_ORGANIZATION.md) for admin-related issues
- Check Django logs: `python manage.py runserver --verbosity 2`
- Verify cache is running: `python manage.py shell` → `from django.core.cache import cache; cache.set('test', 1)`

---

**Last Updated**: 2026-01-08  
**Author**: Development Team  
**Status**: Production Ready ✅
