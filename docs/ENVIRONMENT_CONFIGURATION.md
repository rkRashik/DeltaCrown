# Environment Configuration Guide

## Overview

This document provides comprehensive documentation for all environment variables used in the DeltaCrown Tournament Engine. It includes configuration for development, staging, and production environments.

## Table of Contents

- [Quick Start](#quick-start)
- [Environment Files](#environment-files)
- [Required Variables](#required-variables)
- [Optional Variables](#optional-variables)
- [Environment-Specific Configuration](#environment-specific-configuration)
- [GitHub Secrets](#github-secrets)
- [Secrets Rotation Policy](#secrets-rotation-policy)
- [Security Best Practices](#security-best-practices)

---

## Quick Start

### Development Setup

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Update the `.env` file with your local configuration:
   ```bash
   # Minimal required configuration for development
   DJANGO_SETTINGS_MODULE=deltacrown.settings.development
   SECRET_KEY=your-secret-key-here
   DATABASE_URL=postgresql://deltacrown:password@localhost:5432/deltacrown
   REDIS_URL=redis://localhost:6379/0
   ```

3. Generate a secure secret key:
   ```bash
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```

---

## Environment Files

### `.env` (Local Development)
- **Location**: Project root
- **Purpose**: Local development configuration
- **Git Status**: **NEVER COMMIT** (in .gitignore)

### `.env.example` (Template)
- **Location**: Project root
- **Purpose**: Template with dummy values
- **Git Status**: Committed to repository

### Environment-Specific Settings
- `deltacrown/settings/development.py` - Development
- `deltacrown/settings/staging.py` - Staging
- `deltacrown/settings/production.py` - Production

---

## Required Variables

### Core Django Configuration

#### `SECRET_KEY`
- **Required**: Yes
- **Description**: Django secret key for cryptographic signing
- **Example**: `django-insecure-abc123xyz789...`
- **Generation**:
  ```bash
  python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
  ```
- **Security**: Must be unique per environment, minimum 50 characters
- **Rotation**: Every 90 days in production

#### `DJANGO_SETTINGS_MODULE`
- **Required**: Yes
- **Description**: Django settings module to use
- **Options**:
  - `deltacrown.settings.development` - Local development
  - `deltacrown.settings.staging` - Staging environment
  - `deltacrown.settings.production` - Production environment
- **Example**: `deltacrown.settings.development`

#### `DEBUG`
- **Required**: No (defaults per environment)
- **Description**: Enable/disable debug mode
- **Values**: `True`, `False`
- **Default**: `True` (development), `False` (staging/production)
- **Security**: **NEVER** set to `True` in production

### Database Configuration

#### `DATABASE_URL`
- **Required**: Yes
- **Description**: PostgreSQL connection string
- **Format**: `postgresql://user:password@host:port/database`
- **Example**: `postgresql://deltacrown:SecurePass123@localhost:5432/deltacrown`
- **Components**:
  - `user`: Database username
  - `password`: Database password
  - `host`: Database host (localhost, IP, or domain)
  - `port`: Database port (default: 5432)
  - `database`: Database name

#### Individual Database Variables (Alternative)
```bash
POSTGRES_USER=deltacrown
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=deltacrown
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```

### Cache Configuration

#### `REDIS_URL`
- **Required**: Yes
- **Description**: Redis connection string
- **Format**: `redis://host:port/db`
- **Example**: `redis://localhost:6379/0`
- **Components**:
  - `host`: Redis host
  - `port`: Redis port (default: 6379)
  - `db`: Redis database number (0-15)

### Email Configuration

#### `EMAIL_BACKEND`
- **Required**: No (defaults per environment)
- **Description**: Django email backend
- **Options**:
  - `django.core.mail.backends.console.EmailBackend` (dev)
  - `django.core.mail.backends.smtp.EmailBackend` (production)
- **Default**: Console (development), SMTP (production)

#### `EMAIL_HOST`
- **Required**: Yes (production)
- **Description**: SMTP server hostname
- **Example**: `smtp.gmail.com`, `smtp.sendgrid.net`

#### `EMAIL_PORT`
- **Required**: No
- **Description**: SMTP server port
- **Default**: `587` (TLS), `465` (SSL)

#### `EMAIL_HOST_USER`
- **Required**: Yes (production)
- **Description**: SMTP username/email
- **Example**: `noreply@deltacrown.com`

#### `EMAIL_HOST_PASSWORD`
- **Required**: Yes (production)
- **Description**: SMTP password or API key
- **Security**: Use app-specific passwords
- **Rotation**: Every 90 days

#### `EMAIL_USE_TLS`
- **Required**: No
- **Description**: Use TLS encryption
- **Values**: `True`, `False`
- **Default**: `True`

#### `DEFAULT_FROM_EMAIL`
- **Required**: No
- **Description**: Default sender email
- **Example**: `DeltaCrown <noreply@deltacrown.com>`

---

## Optional Variables

### AWS S3 Configuration (Media Storage)

#### `USE_S3`
- **Description**: Enable AWS S3 for media storage
- **Values**: `True`, `False`
- **Default**: `False`

#### `AWS_ACCESS_KEY_ID`
- **Description**: AWS access key
- **Required**: Yes (if USE_S3=True)

#### `AWS_SECRET_ACCESS_KEY`
- **Description**: AWS secret access key
- **Required**: Yes (if USE_S3=True)
- **Security**: Never commit, rotate every 90 days

#### `AWS_STORAGE_BUCKET_NAME`
- **Description**: S3 bucket name
- **Example**: `deltacrown-media`

#### `AWS_S3_REGION_NAME`
- **Description**: AWS region
- **Example**: `us-east-1`, `ap-south-1`

#### `AWS_S3_CUSTOM_DOMAIN`
- **Description**: Custom CloudFront domain
- **Example**: `cdn.deltacrown.com`

### Sentry Configuration (Error Tracking)

#### `SENTRY_DSN`
- **Description**: Sentry DSN for error tracking
- **Example**: `https://abc123@sentry.io/123456`
- **Required**: Recommended for staging/production

#### `SENTRY_ENVIRONMENT`
- **Description**: Environment tag in Sentry
- **Options**: `development`, `staging`, `production`

### Security Settings

#### `ALLOWED_HOSTS`
- **Description**: Comma-separated list of allowed hosts
- **Example**: `deltacrown.com,www.deltacrown.com,staging.deltacrown.com`
- **Required**: Yes (production)

#### `CSRF_TRUSTED_ORIGINS`
- **Description**: Comma-separated list of trusted origins
- **Example**: `https://deltacrown.com,https://www.deltacrown.com`

#### `CORS_ALLOWED_ORIGINS`
- **Description**: Comma-separated list of allowed CORS origins
- **Example**: `https://app.deltacrown.com,https://admin.deltacrown.com`

### JWT Configuration

#### `JWT_ACCESS_TOKEN_LIFETIME`
- **Description**: Access token lifetime in minutes
- **Default**: `60` (1 hour)

#### `JWT_REFRESH_TOKEN_LIFETIME`
- **Description**: Refresh token lifetime in days
- **Default**: `7` (7 days)

### Performance Settings

#### `CONN_MAX_AGE`
- **Description**: Database connection max age in seconds
- **Default**: `600` (10 minutes)

#### `CACHE_TTL`
- **Description**: Default cache TTL in seconds
- **Default**: `300` (5 minutes)

---

## Environment-Specific Configuration

### Development Environment

```bash
# Core
DJANGO_SETTINGS_MODULE=deltacrown.settings.development
DEBUG=True
SECRET_KEY=dev-secret-key-not-for-production

# Database
DATABASE_URL=postgresql://deltacrown:devpass@localhost:5432/deltacrown

# Cache
REDIS_URL=redis://localhost:6379/0

# Email (console backend)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend

# Hosts
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0
```

### Staging Environment

```bash
# Core
DJANGO_SETTINGS_MODULE=deltacrown.settings.staging
DEBUG=False
SECRET_KEY=staging-secret-key-unique-value

# Database
DATABASE_URL=postgresql://deltacrown:stagingpass@staging-db:5432/deltacrown

# Cache
REDIS_URL=redis://staging-redis:6379/0

# Email
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=staging@deltacrown.com
EMAIL_HOST_PASSWORD=app-specific-password
EMAIL_USE_TLS=True

# Security
ALLOWED_HOSTS=staging.deltacrown.com
CSRF_TRUSTED_ORIGINS=https://staging.deltacrown.com

# Sentry
SENTRY_DSN=https://your-sentry-dsn-here
SENTRY_ENVIRONMENT=staging
```

### Production Environment

```bash
# Core
DJANGO_SETTINGS_MODULE=deltacrown.settings.production
DEBUG=False
SECRET_KEY=production-secret-key-highly-secure

# Database (use managed database)
DATABASE_URL=postgresql://deltacrown:productionpass@prod-db:5432/deltacrown

# Cache (use managed Redis)
REDIS_URL=redis://prod-redis:6379/0

# Email (use transactional email service)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=your-sendgrid-api-key
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=DeltaCrown <noreply@deltacrown.com>

# Security
ALLOWED_HOSTS=deltacrown.com,www.deltacrown.com
CSRF_TRUSTED_ORIGINS=https://deltacrown.com,https://www.deltacrown.com
CORS_ALLOWED_ORIGINS=https://app.deltacrown.com

# AWS S3
USE_S3=True
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_STORAGE_BUCKET_NAME=deltacrown-media
AWS_S3_REGION_NAME=ap-south-1
AWS_S3_CUSTOM_DOMAIN=cdn.deltacrown.com

# Sentry
SENTRY_DSN=https://your-production-sentry-dsn
SENTRY_ENVIRONMENT=production
```

---

## GitHub Secrets

### Required Secrets for CI/CD

Navigate to: `Settings → Secrets and variables → Actions`

#### Core Secrets
```yaml
# Django
DJANGO_SECRET_KEY: "your-secret-key"
DJANGO_SETTINGS_MODULE: "deltacrown.settings.production"

# Database
DATABASE_URL: "postgresql://user:pass@host:5432/db"
POSTGRES_PASSWORD: "your-postgres-password"

# Email
EMAIL_HOST_USER: "noreply@deltacrown.com"
EMAIL_HOST_PASSWORD: "your-email-password"

# AWS
AWS_ACCESS_KEY_ID: "your-aws-key"
AWS_SECRET_ACCESS_KEY: "your-aws-secret"
AWS_STORAGE_BUCKET_NAME: "deltacrown-media"

# Sentry
SENTRY_DSN: "your-sentry-dsn"

# Deployment
STAGING_SSH_KEY: "your-staging-ssh-private-key"
STAGING_SERVER_IP: "192.168.1.100"
STAGING_SSH_USER: "deploy"
PRODUCTION_SSH_KEY: "your-production-ssh-private-key"
PRODUCTION_SERVER_IP: "192.168.1.200"
PRODUCTION_SSH_USER: "deploy"

# Docker
DOCKER_USERNAME: "your-docker-username"
DOCKER_PASSWORD: "your-docker-password"
```

#### Optional Secrets
```yaml
# Slack Notifications
SLACK_WEBHOOK_URL: "https://hooks.slack.com/services/YOUR/WEBHOOK"

# Discord Notifications
DISCORD_WEBHOOK_URL: "https://discord.com/api/webhooks/YOUR/WEBHOOK"

# CodeCov
CODECOV_TOKEN: "your-codecov-token"
```

---

## Secrets Rotation Policy

### Rotation Schedule

| Secret Type | Rotation Frequency | Priority |
|------------|-------------------|----------|
| Django SECRET_KEY | 90 days | High |
| Database passwords | 90 days | High |
| AWS credentials | 90 days | High |
| Email passwords | 90 days | Medium |
| SSH keys | 180 days | High |
| API tokens | 60 days | Medium |

### Rotation Process

1. **Generate New Secret**
   ```bash
   # Django secret key
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   
   # Random password
   openssl rand -base64 32
   ```

2. **Update Secrets**
   - GitHub Secrets: `Settings → Secrets → Edit`
   - Environment files: Update `.env` locally
   - Server: Update environment variables

3. **Deploy Changes**
   - Staging: Test rotation in staging first
   - Production: Schedule maintenance window
   - Verify: Test application after rotation

4. **Document Rotation**
   - Record rotation date
   - Update LastPass/1Password
   - Notify team

### Emergency Rotation

If a secret is compromised:

1. **Immediate Action**
   - Rotate the compromised secret immediately
   - Revoke API keys/tokens
   - Reset passwords

2. **Investigation**
   - Check access logs
   - Identify breach source
   - Document incident

3. **Prevention**
   - Update security policies
   - Review access controls
   - Implement additional monitoring

---

## Security Best Practices

### ✅ Do

- ✅ Use strong, unique passwords for each environment
- ✅ Store secrets in secure vaults (LastPass, 1Password)
- ✅ Rotate secrets regularly (see schedule above)
- ✅ Use environment-specific secrets
- ✅ Enable MFA for AWS, GitHub, and other services
- ✅ Use app-specific passwords for email
- ✅ Encrypt secrets in transit and at rest
- ✅ Limit secret access to necessary personnel
- ✅ Use GitHub secret scanning
- ✅ Monitor secret usage and access

### ❌ Don't

- ❌ Commit secrets to version control
- ❌ Share secrets via email or chat
- ❌ Use same secret across environments
- ❌ Store secrets in plaintext files
- ❌ Reuse passwords
- ❌ Share AWS root credentials
- ❌ Disable security features for convenience
- ❌ Use weak or default passwords
- ❌ Store secrets in code comments
- ❌ Log secrets to console or files

### Secret Management Tools

#### Recommended Tools

1. **GitHub Secrets** - For CI/CD
2. **AWS Secrets Manager** - For production secrets
3. **HashiCorp Vault** - For enterprise secret management
4. **1Password** / **LastPass** - For team password sharing
5. **django-environ** - For local environment variables

#### Checking for Leaked Secrets

```bash
# Install pre-commit hooks
pre-commit install

# Scan for secrets
pre-commit run detect-secrets --all-files

# Create secrets baseline
detect-secrets scan > .secrets.baseline
```

---

## Troubleshooting

### Common Issues

#### "ImproperlyConfigured: Set the SECRET_KEY"
- **Cause**: SECRET_KEY not set or invalid
- **Fix**: Set SECRET_KEY in environment or .env file

#### "OperationalError: FATAL: password authentication failed"
- **Cause**: Invalid database credentials
- **Fix**: Verify DATABASE_URL format and credentials

#### "Connection to Redis refused"
- **Cause**: Redis not running or incorrect URL
- **Fix**: Start Redis and verify REDIS_URL

#### "SMTPAuthenticationError"
- **Cause**: Invalid email credentials
- **Fix**: Use app-specific password, check EMAIL_HOST_PASSWORD

---

## References

- [Django Settings Documentation](https://docs.djangoproject.com/en/4.2/ref/settings/)
- [12-Factor App Methodology](https://12factor.net/config)
- [OWASP Secret Management](https://owasp.org/www-community/SecretManagement)
- [GitHub Secrets Documentation](https://docs.github.com/en/actions/security-guides/encrypted-secrets)

---

**Last Updated**: November 4, 2025  
**Document Version**: 1.0  
**Status**: ✅ Complete (DO-003)
