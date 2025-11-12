# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in DeltaCrown, please report it by:

1. **Email**: Contact the repository owner directly (do not create public issues for security vulnerabilities)
2. **GitHub Security Advisories**: Use the "Security" tab to report privately
3. **Expected Response Time**: We aim to respond within 48 hours

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 6.6.x   | :white_check_mark: |
| 6.5.x   | :white_check_mark: |
| < 6.0   | :x:                |

## Security Measures

### Authentication & Authorization
- Django Allauth for user authentication
- Role-based access control (RBAC) for admin/staff
- Session management with secure cookies
- CSRF protection enabled

### Data Protection
- PII handling guidelines (see `docs/OPERATIONS_S3_CHECKS.md`)
- Encrypted storage for sensitive data
- S3 bucket policies for media access control
- Database query optimization to prevent information leakage

### Infrastructure Security
- HTTPS-only in production (enforced by middleware)
- Security headers (CSP, HSTS, X-Frame-Options)
- Rate limiting on API endpoints
- Regular dependency updates via `pip-audit`

## CI/CD Security

### Workflow Credentials
All CI/CD workflows follow secure secret management practices:

- **No hardcoded credentials** in workflow files
- GitHub Actions secrets for sensitive values (`PERF_DB_PASSWORD`, `AWS_*`, etc.)
- Ephemeral credentials for PR checks (no repository secrets required)
- Service networking via hostnames (not exposed ports)

**Evidence & Controls**: See [`docs/ci/perf-secrets-hotfix.md`](docs/ci/perf-secrets-hotfix.md) for:
- Before/after diffs of workflow sanitization
- Secret masking patterns (`::add-mask::`)
- Least-privilege permissions (explicit in workflows)
- Automated guardrails (workflow lint + GitLeaks)

### Automated Secret Scanning
- **GitLeaks**: Custom config (`.gitleaks.toml`) for DeltaCrown patterns
- **GitHub Secret Scanning**: Enabled for common credential types
- **Workflow Guard**: CI job rejects hardcoded passwords/keys

### Branch Protection
Required status checks on `master`:
- Perf Smoke (PR-safe performance tests)
- Workflow Secrets Guard (automated credential lint)
- Core test suite (pytest)

## Incident Response

### Recent Security Incidents
For transparency, we log resolved security issues:

| Date       | Type                  | Severity | Status   | Details                           |
|------------|-----------------------|----------|----------|-----------------------------------|
| 2025-11-12 | Hardcoded DB Password | LOW      | Resolved | [Hotfix: ci-perf-secrets](docs/ci/perf-secrets-hotfix.md) |

### Response Procedure
1. **Identify**: Automated scans or manual report
2. **Contain**: Create hotfix branch, rotate credentials
3. **Remediate**: Implement fix, add guardrails
4. **Verify**: Evidence bundle + green CI checks
5. **Document**: Update security log + docs

## Best Practices for Contributors

### Code Security
- Never commit credentials, API keys, or tokens
- Use environment variables for secrets
- Follow Django security best practices
- Sanitize user inputs (leverage Django ORM)

### Dependency Management
- Run `pip-audit` before pull requests
- Update dependencies regularly (monitor Dependabot alerts)
- Pin versions in `requirements.txt`

### Workflow Development
- Use GitHub Actions secrets for sensitive values
- Set explicit permissions (principle of least privilege)
- Add secret masking (`::add-mask::`) for defense in depth
- Gate external uploads to `schedule` or `push to master` only

## Security Contacts

- **Repository Owner**: rkRashik (GitHub)
- **Security Team**: (to be established)

## Acknowledgments

We appreciate responsible disclosure and will credit security researchers who report vulnerabilities (with their permission).
