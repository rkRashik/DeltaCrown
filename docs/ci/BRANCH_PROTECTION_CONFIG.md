# Branch Protection Configuration

This document outlines the required branch protection rules for the DeltaCrown repository.

## Protected Branch: `master`

### Required Status Checks

The following CI checks **must pass** before merging to `master`:

#### 1. Perf Smoke (`perf-smoke`)
- **Workflow**: `.github/workflows/perf-smoke.yml`
- **Purpose**: Fast performance regression detection on PRs
- **Credentials**: Ephemeral (no repository secrets required)
- **Runtime**: ~2-3 minutes (50 samples)
- **Failure Criteria**: 
  - Any SLO violation (p95 exceeds baseline threshold)
  - Test failures (assertion errors, exceptions)
  - Coverage regression (below gate)

#### 2. Workflow Secrets Guard (`guard-workflow-secrets`)
- **Workflow**: `.github/workflows/guard-workflow-secrets.yml`
- **Purpose**: Automated credential lint to prevent hardcoded secrets
- **Triggers**: PR changes to `.github/workflows/` directory
- **Checks**:
  - No hardcoded `PASSWORD:` or `SECRET:` without `${{ secrets.* }}`
  - No `postgres://` URLs with embedded credentials
  - No common weak passwords (password, admin, test, etc.)
  - Warnings for unnecessary port mappings
- **Failure Criteria**:
  - Any hardcoded credentials detected
  - Regex pattern violations

#### 3. Core Test Suite (`pytest`)
- **Workflow**: (primary test workflow, e.g., `.github/workflows/django.yml`)
- **Purpose**: Full test suite execution
- **Coverage Gates**:
  - Overall: ≥67%
  - Critical modules: ≥72%
- **Failure Criteria**:
  - Test failures
  - Coverage regression
  - Import errors or environment issues

### Configuration Steps

#### Via GitHub Web UI

1. Navigate to: **Settings → Branches → Branch protection rules**
2. Click **Add rule** (or edit existing rule for `master`)
3. Enable:
   - ✅ **Require a pull request before merging**
     - Require approvals: 1 (for teams)
   - ✅ **Require status checks to pass before merging**
     - Search and add:
       - `perf-smoke`
       - `guard-workflow-secrets`
       - `pytest` (or your core test job name)
     - ✅ **Require branches to be up to date before merging**
   - ✅ **Require conversation resolution before merging**
   - ✅ **Do not allow bypassing the above settings** (if applicable)

4. Click **Create** or **Save changes**

#### Via GitHub CLI

```bash
# Set required status checks
gh api repos/rkRashik/DeltaCrown/branches/master/protection \
  --method PUT \
  --field required_status_checks[strict]=true \
  --field required_status_checks[contexts][]=perf-smoke \
  --field required_status_checks[contexts][]=guard-workflow-secrets \
  --field required_status_checks[contexts][]=pytest \
  --field enforce_admins=false \
  --field required_pull_request_reviews[required_approving_review_count]=1 \
  --field required_conversation_resolution[enabled]=true
```

#### Via Terraform (Infrastructure as Code)

```hcl
resource "github_branch_protection" "master" {
  repository_id = "DeltaCrown"
  pattern       = "master"

  required_status_checks {
    strict   = true
    contexts = [
      "perf-smoke",
      "guard-workflow-secrets",
      "pytest"
    ]
  }

  required_pull_request_reviews {
    required_approving_review_count = 1
  }

  required_conversation_resolution = true
  enforce_admins                   = false
}
```

## Additional Recommendations

### Optional Status Checks (Non-Blocking)
- **Perf Baseline** (`perf-baseline`): Nightly only, not required for PRs
- **S3 Chaos Tests** (`test-s3-chaos`): Long-running, optional for PRs
- **GitLeaks Scan** (`gitleaks`): If integrated as separate workflow

### Rulesets (Future Enhancement)
Consider GitHub Rulesets (beta) for more granular control:
- Deployment protection rules
- Tag protection
- Commit signature verification

### Notification Settings
Configure CODEOWNERS to auto-assign reviewers:
```plaintext
# .github/CODEOWNERS
/.github/workflows/  @rkRashik
/docs/ci/            @rkRashik
/SECURITY.md         @rkRashik
```

## Troubleshooting

### Status Check Not Appearing
1. **Verify workflow runs**: Ensure the workflow has run at least once on a PR
2. **Check job names**: Status check name must match the job `name:` in workflow YAML
3. **Branch consistency**: Workflow must target the same branch as the protection rule

### Bypassing Checks (Emergency Only)
**Admin users** can bypass checks if `enforce_admins` is disabled:
1. Navigate to PR
2. Click **Merge without waiting for requirements**
3. **Document reason** in PR comments (emergency hotfix, etc.)

**Post-merge action**: 
- Revert if necessary
- Fix root cause
- Re-run checks on follow-up PR

## Verification

After configuration, verify:

```bash
# Check protection status
gh api repos/rkRashik/DeltaCrown/branches/master/protection | jq '.required_status_checks.contexts'

# Expected output:
# [
#   "perf-smoke",
#   "guard-workflow-secrets",
#   "pytest"
# ]
```

## Related Documentation

- [Security Policy](../../SECURITY.md) - Overall security measures
- [Perf Secrets Hotfix Evidence](perf-secrets-hotfix.md) - Workflow credential handling
- [Operations S3 Checks](../OPERATIONS_S3_CHECKS.md) - Storage integrity procedures
- [Performance Runbook](../PERF_RUNBOOK.md) - SLO baselines and tuning

## Changelog

| Date       | Change                          | Author   |
|------------|---------------------------------|----------|
| 2025-11-12 | Initial branch protection setup | rkRashik |
