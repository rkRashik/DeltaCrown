# GitHub Repository Setup Guide

## Overview

This document outlines the GitHub repository configuration, branch protection rules, and workflow guidelines for the DeltaCrown Tournament Engine project.

## Repository Information

- **Repository**: DeltaCrown
- **Owner**: rkRashik
- **Visibility**: Private/Public
- **Primary Branch**: master
- **Branch Strategy**: Single master branch (no feature branches)

## Repository Settings

### General Settings

Navigate to: `Settings → General`

```yaml
Repository name: DeltaCrown
Description: "Enterprise-grade tournament management platform for esports competitions"
Website: https://deltacrown.com
Topics: django, esports, tournament, python, postgresql, redis, docker, jwt
```

**Features to Enable:**
- ✅ Issues
- ✅ Projects
- ✅ Discussions
- ✅ Wiki
- ✅ Sponsors (if applicable)

**Features to Disable:**
- ❌ Allow merge commits (use squash or rebase instead)
- ❌ Allow rebase merging (use squash for cleaner history)

### Collaborators and Teams

Navigate to: `Settings → Collaborators and teams`

**Admin Access:**
- @rkRashik (Owner)

**Write Access:**
- Add team members as needed

**Read Access:**
- Add external reviewers if needed

## Branch Protection Rules

### Configure Master Branch Protection

Navigate to: `Settings → Branches → Branch protection rules → Add rule`

**Branch name pattern**: `master`

#### Protection Settings

**Require a pull request before merging:**
- ✅ Require approvals: 1
- ✅ Dismiss stale pull request approvals when new commits are pushed
- ✅ Require review from Code Owners
- ❌ Restrict who can dismiss pull request reviews (only for larger teams)
- ✅ Allow specified actors to bypass required pull requests (owner only)

**Require status checks to pass before merging:**
- ✅ Require branches to be up to date before merging
- **Required status checks:**
  - `CI / lint`
  - `CI / test-python-3.11`
  - `CI / security-check`
  - `CI / build-docker`

**Require conversation resolution before merging:**
- ✅ Enabled (all comments must be resolved)

**Require signed commits:**
- ✅ Enabled (recommended for security)

**Require linear history:**
- ✅ Enabled (keeps history clean)

**Include administrators:**
- ❌ Disabled (allows emergency fixes by admin)

**Restrict who can push to matching branches:**
- ✅ Enabled
- **Allowed actors:** Administrators only

**Allow force pushes:**
- ❌ Disabled (protects history)

**Allow deletions:**
- ❌ Disabled (prevents accidental deletion)

### Lock Branch (Optional)

For production releases, you can temporarily lock the branch:
- Navigate to: `Settings → Branches → master → Edit`
- Enable: "Lock branch"

## Required Configuration Files

### ✅ Completed Files

- `.github/pull_request_template.md` - PR template
- `.github/ISSUE_TEMPLATE/bug_report.md` - Bug report template
- `.github/ISSUE_TEMPLATE/feature_request.md` - Feature request template
- `.github/ISSUE_TEMPLATE/documentation.md` - Documentation template
- `.github/ISSUE_TEMPLATE/config.yml` - Issue template configuration
- `.github/CODEOWNERS` - Code ownership assignments
- `CONTRIBUTING.md` - Contribution guidelines

### 🔜 Upcoming Files (DO-002)

- `.github/workflows/ci.yml` - CI/CD pipeline
- `.github/workflows/deploy-staging.yml` - Staging deployment
- `.github/workflows/security-scan.yml` - Security scanning

## GitHub Actions Secrets

Navigate to: `Settings → Secrets and variables → Actions`

### Required Secrets

```yaml
# Database
DATABASE_URL: postgresql://user:password@host:5432/dbname
POSTGRES_PASSWORD: your_postgres_password

# Django
DJANGO_SECRET_KEY: your_secret_key_here
DJANGO_SETTINGS_MODULE: deltacrown.settings.production

# AWS (if using S3)
AWS_ACCESS_KEY_ID: your_aws_access_key
AWS_SECRET_ACCESS_KEY: your_aws_secret_key
AWS_STORAGE_BUCKET_NAME: deltacrown-media

# Email
EMAIL_HOST_USER: noreply@deltacrown.com
EMAIL_HOST_PASSWORD: your_email_password

# Sentry
SENTRY_DSN: your_sentry_dsn

# Deployment
SSH_PRIVATE_KEY: your_deployment_ssh_key
STAGING_SERVER_IP: 192.168.1.100
PRODUCTION_SERVER_IP: 192.168.1.200

# Docker
DOCKER_USERNAME: your_docker_username
DOCKER_PASSWORD: your_docker_password

# GitHub Token (auto-created)
GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### Required Variables

Navigate to: `Settings → Secrets and variables → Actions → Variables`

```yaml
PYTHON_VERSION: "3.11"
NODE_VERSION: "20"
POSTGRES_VERSION: "15"
REDIS_VERSION: "7"
DOCKER_REGISTRY: ghcr.io
IMAGE_NAME: ghcr.io/rkrashik/deltacrown
```

## Code Scanning

### Configure Dependabot

Navigate to: `Settings → Security → Code security and analysis`

**Enable:**
- ✅ Dependency graph
- ✅ Dependabot alerts
- ✅ Dependabot security updates

Create `.github/dependabot.yml`:

```yaml
version: 2
updates:
  # Python dependencies
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 10
    reviewers:
      - "rkRashik"
    labels:
      - "dependencies"
      - "python"
  
  # Docker dependencies
  - package-ecosystem: "docker"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 5
    reviewers:
      - "rkRashik"
    labels:
      - "dependencies"
      - "docker"
  
  # GitHub Actions
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 5
    reviewers:
      - "rkRashik"
    labels:
      - "dependencies"
      - "ci"
```

### Enable Code Scanning

Navigate to: `Settings → Security → Code security and analysis`

**Enable:**
- ✅ Code scanning (CodeQL)
- ✅ Secret scanning
- ✅ Secret scanning push protection

## Webhook Configuration (Optional)

For CI/CD integrations, Slack notifications, etc.

Navigate to: `Settings → Webhooks → Add webhook`

**Example - Slack Notifications:**
```
Payload URL: https://hooks.slack.com/services/YOUR/WEBHOOK/URL
Content type: application/json
Events: Push, Pull request, Issues, Issue comments
```

## GitHub Projects

### Create Project Board

Navigate to: `Projects → New project`

**Project Settings:**
- Name: "DeltaCrown Development"
- Description: "Sprint planning and task tracking"
- Template: "Automated kanban"

**Columns:**
- 📋 Backlog
- 🎯 Sprint Planning
- 🏗️ In Progress
- 👀 In Review
- ✅ Done
- 🚀 Deployed

**Automation:**
- New issues → Backlog
- Issues assigned → In Progress
- PR opened → In Review
- PR merged → Done

## Labels

Navigate to: `Issues → Labels → New label`

### Priority Labels
```
priority: critical   - #d73a4a (red)
priority: high       - #ff9800 (orange)
priority: medium     - #ffc107 (yellow)
priority: low        - #4caf50 (green)
```

### Type Labels
```
bug                  - #d73a4a (red)
enhancement          - #a2eeef (light blue)
documentation        - #0075ca (blue)
security             - #ee0701 (dark red)
performance          - #9c27b0 (purple)
```

### Status Labels
```
status: in-progress  - #fbca04 (yellow)
status: blocked      - #d73a4a (red)
status: needs-review - #0e8a16 (green)
status: needs-info   - #d876e3 (pink)
```

### Sprint Labels
```
sprint-1             - #1d76db (blue)
sprint-2             - #1d76db (blue)
sprint-3             - #1d76db (blue)
```

### Category Labels
```
backend              - #5319e7 (purple)
frontend             - #bfd4f2 (light blue)
devops               - #d4c5f9 (lavender)
database             - #c2e0c6 (light green)
api                  - #bfdadc (cyan)
```

## Milestones

Navigate to: `Issues → Milestones → New milestone`

**Sprint 1 (Week 1):**
- Title: "Sprint 1 - Foundation"
- Due date: [Set date]
- Description: "Core infrastructure and authentication"

**Sprint 2 (Week 2):**
- Title: "Sprint 2 - User Management"
- Due date: [Set date]
- Description: "User profiles and team management"

## Repository Badges

Add to README.md:

```markdown
[![CI Status](https://github.com/rkRashik/DeltaCrown/workflows/CI/badge.svg)](https://github.com/rkRashik/DeltaCrown/actions)
[![codecov](https://codecov.io/gh/rkRashik/DeltaCrown/branch/master/graph/badge.svg)](https://codecov.io/gh/rkRashik/DeltaCrown)
[![Python Version](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Django Version](https://img.shields.io/badge/django-4.2+-green.svg)](https://www.djangoproject.com/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
```

## Workflow Best Practices

### For All Contributors

1. **Always pull latest changes before starting work**
   ```bash
   git pull origin master
   ```

2. **Make atomic commits with clear messages**
   ```bash
   git commit -m "feat(auth): add JWT token refresh endpoint"
   ```

3. **Push frequently to avoid conflicts**
   ```bash
   git push origin master
   ```

4. **Run tests before pushing**
   ```bash
   pytest && flake8 && mypy apps/
   ```

### For Maintainers

1. **Review PRs promptly** (within 24 hours)
2. **Test PRs locally** before merging
3. **Ensure CI passes** before merging
4. **Use squash merge** to keep history clean
5. **Update changelog** after merging significant changes

### Emergency Hotfix Process

For critical production issues:

1. Notify team in Slack/Discord
2. Create issue with `priority: critical` label
3. Make fix directly on master
4. Test thoroughly
5. Deploy immediately
6. Document in changelog

## Security Best Practices

### Commit Signing

Enable GPG commit signing:

```bash
# Generate GPG key
gpg --full-generate-key

# List keys
gpg --list-secret-keys --keyid-format=long

# Configure git
git config --global user.signingkey YOUR_KEY_ID
git config --global commit.gpgsign true

# Add to GitHub
gpg --armor --export YOUR_KEY_ID
# Paste in Settings → SSH and GPG keys → New GPG key
```

### Secret Scanning

Never commit:
- Passwords or API keys
- Database credentials
- AWS credentials
- Private keys
- Session tokens

Use environment variables or secrets manager.

### Two-Factor Authentication

Enable 2FA for all collaborators:
- Navigate to: `Settings → Password and authentication`
- Enable: "Two-factor authentication"

## Monitoring and Metrics

### Repository Insights

Navigate to: `Insights` to view:
- Pulse (activity summary)
- Contributors (contribution stats)
- Community (health check)
- Traffic (page views, clones)
- Commits (commit history)
- Code frequency (additions/deletions)
- Dependency graph
- Network (branch visualization)

### Recommended Integrations

- **CodeCov**: Test coverage reporting
- **Sentry**: Error tracking
- **Better Uptime**: Uptime monitoring
- **Slack/Discord**: Team notifications

## Maintenance Schedule

### Daily
- Monitor CI/CD pipelines
- Review and merge PRs
- Respond to issues

### Weekly
- Review dependency updates (Dependabot)
- Update project board
- Sprint planning meetings

### Monthly
- Security audit
- Performance review
- Documentation updates
- Dependency cleanup

## Troubleshooting

### CI Failing

1. Check workflow logs in Actions tab
2. Run tests locally: `pytest`
3. Verify all secrets are configured
4. Check branch protection rules

### Cannot Push to Master

1. Verify you have write access
2. Check if branch is locked
3. Ensure commit is signed (if required)
4. Pull latest changes first

### Merge Conflicts

```bash
git pull origin master
# Resolve conflicts in files
git add .
git commit -m "chore: resolve merge conflicts"
git push origin master
```

## References

- [GitHub Docs - Branch Protection](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/defining-the-mergeability-of-pull-requests/about-protected-branches)
- [GitHub Docs - Code Owners](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners)
- [GitHub Docs - Actions Secrets](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [Conventional Commits](https://www.conventionalcommits.org/)

---

**Last Updated**: November 4, 2025
**Status**: ✅ Complete (DO-001)
**Next**: DO-002 CI/CD Pipeline Setup
