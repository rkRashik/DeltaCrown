# DeltaCrown Tournament Engine - Development Guidelines

**Version:** 1.0  
**Date:** November 4, 2025  
**Status:** Active  
**Phase:** Development (Sprints 1-16)

---

## 🎯 Overview

This document defines the development workflow, branching strategy, code standards, and quality gates for the DeltaCrown Tournament Engine project. All developers must follow these guidelines strictly.

---

## 🌿 Branching Strategy

### **Single Master Branch Approach**

The project uses **ONLY the `master` branch** for all development work throughout the 16-week build cycle.

#### Branch Structure

```
master (ONLY BRANCH - all work happens here)
   ↓
All commits go directly to master
No other branches exist
```

#### Key Principles

1. **One Branch, One Team**
   - All developers work on the same `master` branch
   - No feature branches, no sprint branches, no development branches
   - All commits are pushed directly to `master`

2. **Continuous Integration**
   - Frequent commits (multiple times per day)
   - Small, atomic commits with clear messages
   - Immediate integration of all changes
   - Conflicts resolved immediately through communication

3. **Protection Rules**
   - `master` branch: Open for all team commits
   - No branch protection needed (single branch only)
   - Tags used for sprint releases

#### Workflow

```bash
# Initial setup (one time)
git clone <repository-url>
cd deltacrown-tournament-engine

# Daily development cycle
git pull origin master  # Always pull latest before starting
# ... make changes ...
git add .
git commit -m "feat: descriptive commit message"
git push origin master  # Push frequently

# End of sprint (weekly)
# Project Lead creates tag for release
git tag -a "sprint-01-release" -m "Sprint 1 Complete"
git push origin master --tags
```

#### Commit Message Convention

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

Types:
- feat: New feature (e.g., feat(auth): add JWT authentication)
- fix: Bug fix (e.g., fix(payment): correct Stripe webhook signature)
- docs: Documentation only (e.g., docs(api): update endpoint specs)
- style: Code style changes (e.g., style(frontend): format with prettier)
- refactor: Code refactoring (e.g., refactor(teams): simplify validation)
- test: Adding tests (e.g., test(registration): add E2E tests)
- chore: Build/config changes (e.g., chore(deps): update Django to 4.2.7)
- perf: Performance improvements (e.g., perf(queries): optimize N+1 queries)

Examples:
✅ feat(registration): implement multi-step registration wizard
✅ fix(stripe): handle webhook idempotency correctly
✅ test(payment): add unit tests for Payment model
✅ docs(sprint-05): update acceptance criteria for FE-022
❌ updated stuff
❌ fixed bug
❌ WIP
```

#### Why Single Branch?

**Benefits:**
- ✅ Immediate visibility of all changes to entire team
- ✅ Early conflict detection and resolution
- ✅ Simpler workflow, less context switching
- ✅ Enforces communication and collaboration
- ✅ Faster integration and feedback loops
- ✅ No stale branches or merge debt

**Requirements:**
- Team must communicate frequently (daily standups essential)
- Code reviews done via pull requests or pair programming
- CI/CD runs on every commit to catch issues early
- Team must coordinate on files being edited

---

## 👥 Team Collaboration

### Daily Workflow

**Morning:**
```bash
# 1. Pull latest changes
git pull origin master

# 2. Check what others are working on (standup)
# Avoid editing same files simultaneously

# 3. Start your work
```

**During Day:**
```bash
# Commit frequently (every 1-2 hours)
git add <files>
git commit -m "feat(scope): what you did"
git push origin master

# Pull regularly to stay in sync
git pull origin master  # Every 2-3 hours
```

**End of Day:**
```bash
# Ensure all work is pushed
git status  # Check for uncommitted changes
git add .
git commit -m "feat(scope): end of day checkpoint"
git push origin master
```

### Conflict Resolution

**When conflicts occur:**

```bash
# 1. Pull and see conflicts
git pull origin master

# 2. Communicate with teammate
# "Hey, I see a conflict in teams/models.py. Let's sync up."

# 3. Resolve conflicts together
# Edit conflicted files
git add <resolved-files>
git commit -m "merge: resolve conflict in teams/models.py"
git push origin master
```

**Prevention:**
- Announce in chat: "Working on `apps/tournaments/models.py`"
- Use pair programming for complex modules
- Break tickets into smaller, file-specific tasks

---

## 📝 Code Standards

### Python/Django Backend

**Style Guide:**
- Follow [PEP 8](https://peps.python.org/pep-0008/)
- Use [Black](https://black.readthedocs.io/) for formatting
- Use [flake8](https://flake8.pycqa.org/) for linting
- Max line length: 100 characters

**Configuration:**
```ini
# setup.cfg
[flake8]
max-line-length = 100
exclude = migrations, __pycache__, venv
ignore = E203, W503

[tool:pytest]
DJANGO_SETTINGS_MODULE = deltacrown.settings_test_pg
python_files = test_*.py
python_classes = Test*
python_functions = test_*
```

**Code Example:**
```python
# ✅ Good
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Tournament(models.Model):
    """
    Represents a gaming tournament with all associated metadata.
    
    Attributes:
        name: Tournament display name
        slug: URL-friendly identifier
        organizer: User who created the tournament
    """
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    organizer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='organized_tournaments'
    )
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse('tournament-detail', kwargs={'slug': self.slug})


# ❌ Bad
class tournament(models.Model):  # Wrong case
    name=models.CharField(max_length=200)  # No spaces around =
    slug=models.SlugField(unique=True)  # Missing docstring
    organizer=models.ForeignKey(User,on_delete=models.CASCADE)
```

### JavaScript/Frontend

**Style Guide:**
- Use [ESLint](https://eslint.org/) with Airbnb config
- Use [Prettier](https://prettier.io/) for formatting
- Prefer `const` over `let`, avoid `var`
- Use arrow functions for callbacks

**Configuration:**
```json
// .eslintrc.json
{
  "extends": ["airbnb-base", "prettier"],
  "env": {
    "browser": true,
    "es2021": true
  },
  "rules": {
    "no-console": "warn",
    "prefer-const": "error",
    "no-var": "error"
  }
}
```

**Code Example:**
```javascript
// ✅ Good
function registrationModal() {
  return {
    currentStep: 1,
    selectedTeam: null,
    
    init() {
      this.loadTeams();
    },
    
    async loadTeams() {
      try {
        const response = await fetch('/api/teams/');
        const teams = await response.json();
        this.teams = teams;
      } catch (error) {
        this.showError('Failed to load teams');
      }
    },
    
    nextStep() {
      if (this.validateCurrentStep()) {
        this.currentStep += 1;
      }
    }
  };
}

// ❌ Bad
function registrationModal() {
  return {
    currentStep: 1,
    selectedTeam: null,
    init: function() {  // Use arrow function
      this.loadTeams()  // Missing semicolon
    },
    loadTeams: function() {  // Should be async
      fetch('/api/teams/').then(function(response) {  // Use arrow functions
        response.json().then(function(teams) {
          this.teams = teams  // `this` is wrong here
        })
      })
    }
  }
}
```

### HTML/Templates

**Standards:**
- Semantic HTML5 elements
- Accessible markup (ARIA labels, roles)
- Proper indentation (2 spaces)
- Lowercase tags and attributes

**Example:**
```html
<!-- ✅ Good -->
<section class="tournament-list" aria-label="Tournament List">
  <h2>Upcoming Tournaments</h2>
  <ul role="list">
    {% for tournament in tournaments %}
    <li class="tournament-card">
      <a href="{{ tournament.get_absolute_url }}" aria-label="View {{ tournament.name }}">
        <h3>{{ tournament.name }}</h3>
        <time datetime="{{ tournament.start_date|date:'Y-m-d' }}">
          {{ tournament.start_date|date:"F j, Y" }}
        </time>
      </a>
    </li>
    {% endfor %}
  </ul>
</section>

<!-- ❌ Bad -->
<div class="tournaments">
  <h2>Upcoming Tournaments</h2>
  <div>
  {% for tournament in tournaments %}
    <div>
      <a href="{{ tournament.get_absolute_url }}">{{ tournament.name }}</a>
      <span>{{ tournament.start_date }}</span>
    </div>
  {% endfor %}
  </div>
</div>
```

---

## ✅ Quality Gates

### Before Every Commit

```bash
# 1. Run tests
pytest  # Backend tests
npm test  # Frontend tests

# 2. Check linting
flake8 apps/
black --check apps/
eslint static/js/

# 3. Check for migrations
python manage.py makemigrations --check --dry-run

# 4. Quick smoke test
python manage.py runserver  # Test locally
```

### Definition of Done (DoD)

Every ticket is considered complete only when:

- [ ] All acceptance criteria met
- [ ] Code follows style guides
- [ ] Unit tests written and passing
- [ ] Integration tests passing (if applicable)
- [ ] No linting errors
- [ ] Code coverage threshold met (>85% backend, >75% frontend)
- [ ] Manual testing completed
- [ ] Documentation updated
- [ ] Code committed and pushed to `development`
- [ ] No console errors or warnings
- [ ] Accessibility checks passed

### Code Review Process

**Pull Request (Optional but Recommended):**

While we use a single branch, PRs can still be used for review:

1. Create PR from `development` to `development` (review-only)
2. Request review from teammate
3. Address feedback
4. Self-merge or close PR (changes already in `development`)

**OR Pair Programming:**

1. Work together on code in real-time
2. Review happens during development
3. Both developers approve before commit

**OR Post-Commit Review:**

1. Push to `development`
2. Notify team in chat: "Pushed BE-014, please review"
3. Team reviews on GitHub/GitLab
4. Feedback addressed in next commit

---

## 🧪 Testing Strategy

### Test Levels

1. **Unit Tests** (pytest for backend, Jest for frontend)
   - Test individual functions/methods
   - Mock external dependencies
   - Fast execution (<1s per test)
   - Run on every commit (CI)

2. **Integration Tests** (pytest-django)
   - Test API endpoints end-to-end
   - Use test database
   - Test authentication, permissions
   - Run on every commit (CI)

3. **E2E Tests** (Playwright)
   - Test complete user flows
   - Run in real browser
   - Test critical paths only
   - Run nightly or before sprint completion

### Coverage Requirements

**Backend:**
```bash
# Run tests with coverage
pytest --cov=apps --cov-report=html --cov-report=term

# Minimum thresholds
# Statements: 85%
# Branches: 80%
# Functions: 85%
# Lines: 85%
```

**Frontend:**
```bash
# Run tests with coverage
npm test -- --coverage

# Minimum thresholds
# Statements: 75%
# Branches: 70%
# Functions: 75%
# Lines: 75%
```

### Test Organization

```
tests/
├── backend/
│   ├── test_tournament_model.py
│   ├── test_registration_api.py
│   ├── test_payment_integration.py
│   └── conftest.py (fixtures)
├── frontend/
│   ├── registration_modal.test.js
│   ├── payment_form.test.js
│   └── setup.js
└── e2e/
    ├── stripe-payment.spec.js
    ├── registration-flow.spec.js
    └── playwright.config.js
```

---

## 🚀 CI/CD Pipeline

### Automated Checks (GitHub Actions)

**On Every Push to `development`:**

```yaml
# .github/workflows/ci.yml
name: Continuous Integration

on:
  push:
    branches: [development]
  pull_request:
    branches: [development]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run migrations
        run: python manage.py migrate
      - name: Run tests
        run: pytest --cov=apps --cov-report=xml
      - name: Check coverage
        run: coverage report --fail-under=85
      - name: Lint
        run: flake8 apps/
  
  frontend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Node
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      - name: Install dependencies
        run: npm ci
      - name: Run tests
        run: npm test -- --coverage
      - name: Lint
        run: npm run lint
```

**On Merge to `master` (End of Sprint):**

```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [master]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run full test suite
        run: |
          pytest
          npm test
          npx playwright test
      - name: Build Docker images
        run: docker-compose build
      - name: Deploy to production
        run: |
          # Deploy steps here
          echo "Deploying to production..."
```

---

## 📦 Dependency Management

### Python Dependencies

```bash
# Always pin versions
# requirements.txt
Django==4.2.7
djangorestframework==3.14.0
stripe==7.4.0
celery==5.3.4

# Update dependencies carefully
pip list --outdated
pip install --upgrade <package>
pip freeze > requirements.txt
```

### JavaScript Dependencies

```bash
# Use exact versions in package.json
npm install <package> --save-exact

# Update dependencies
npm outdated
npm update <package>

# Security audit
npm audit
npm audit fix
```

---

## 🔒 Security Best Practices

### Environment Variables

**Never commit secrets!**

```python
# ✅ Good - Use environment variables
# settings.py
import os
from environ import Env

env = Env()

SECRET_KEY = env('SECRET_KEY')
STRIPE_SECRET_KEY = env('STRIPE_SECRET_KEY')
DATABASE_URL = env('DATABASE_URL')

# .env (add to .gitignore!)
SECRET_KEY=your-secret-key-here
STRIPE_SECRET_KEY=sk_test_...
DATABASE_URL=postgresql://...
```

```bash
# .gitignore
.env
.env.local
*.secret
credentials.json
```

### Security Checklist

- [ ] No hardcoded passwords or API keys
- [ ] CSRF protection enabled (Django default)
- [ ] SQL injection prevention (use ORM, not raw SQL)
- [ ] XSS prevention (Django auto-escapes templates)
- [ ] HTTPS enforced in production
- [ ] Rate limiting on authentication endpoints
- [ ] Input validation on all forms
- [ ] Secure cookie settings (HttpOnly, Secure, SameSite)

---

## 📊 Sprint Workflow

### Weekly Sprint Cycle

**Monday (Sprint Start):**
- Sprint planning meeting (2 hours)
- Review sprint document
- Assign tickets to developers
- Set sprint goal

**Tuesday-Thursday (Development):**
- Daily standup (15 minutes, 10:00 AM)
  * What did I do yesterday?
  * What will I do today?
  * Any blockers?
- Development work on tickets
- Push to `development` frequently
- Help teammates with blockers

**Friday (Sprint End):**
- Morning: Final commits, testing
- Afternoon: Sprint review (1 hour)
  * Demo completed tickets
  * Review acceptance criteria
  * Show progress to stakeholders
- End of day: Sprint retrospective (30 minutes)
  * What went well?
  * What could improve?
  * Action items for next sprint
- Merge `development` → `master`
- Tag release: `sprint-XX-release`

---

## 🎯 Ticket Workflow

### Ticket States

```
📋 TODO → 🔨 IN PROGRESS → 👀 REVIEW → ✅ DONE
```

**TODO:**
- Ticket in sprint backlog
- Not yet started
- Ready for pickup

**IN PROGRESS:**
- Developer actively working
- Update ticket with progress notes
- Link commits in ticket comments

**REVIEW:**
- Code complete
- Awaiting peer review
- All tests passing

**DONE:**
- Review approved
- Merged to `development`
- Meets Definition of Done

### Ticket Updates

```bash
# Commit message links to ticket
git commit -m "feat(auth): implement JWT authentication [BE-001]"

# GitHub/GitLab auto-links commits to ticket
# Team can see all commits for a ticket
```

---

## 🛠️ Development Tools

### Required Tools

**Backend:**
- Python 3.11+
- pip / pipenv / poetry
- PostgreSQL 14+
- Redis 7+
- Docker & Docker Compose

**Frontend:**
- Node.js 18+
- npm or yarn
- Modern browser (Chrome/Firefox)

**Version Control:**
- Git 2.x
- GitHub account

**IDE/Editor:**
- VS Code (recommended) with extensions:
  - Python
  - Pylance
  - Django
  - ESLint
  - Prettier
  - GitLens

### Recommended VS Code Settings

```json
// .vscode/settings.json
{
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.fixAll.eslint": true
  },
  "[javascript]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  },
  "[python]": {
    "editor.defaultFormatter": "ms-python.black-formatter"
  }
}
```

---

## 📞 Communication

### Daily Communication

**Required:**
- Daily standup (15 min, 10:00 AM)
- Respond to team messages within 2 hours
- Announce when working on specific files
- Report blockers immediately

**Tools:**
- Slack/Discord: Team chat
- GitHub: Code, issues, reviews
- Zoom/Meet: Video calls
- Shared document: Sprint progress tracking

### Escalation

**Issue Levels:**
- **Level 1:** Team discussion (most questions)
- **Level 2:** Tech Lead (architecture, complex bugs)
- **Level 3:** Project Lead (scope changes, priorities)

---

## 📚 Documentation

### Code Documentation

**Python:**
```python
def create_tournament(user, data):
    """
    Create a new tournament with validation.
    
    Args:
        user (User): The organizer creating the tournament
        data (dict): Tournament data including name, dates, game
        
    Returns:
        Tournament: Created tournament instance
        
    Raises:
        ValidationError: If tournament data is invalid
        PermissionDenied: If user cannot create tournaments
        
    Example:
        >>> tournament = create_tournament(user, {
        ...     'name': 'Summer Cup',
        ...     'game': 'valorant'
        ... })
    """
    # Implementation
```

**JavaScript:**
```javascript
/**
 * Fetch user's teams from API
 * @async
 * @param {string} userId - User ID to fetch teams for
 * @returns {Promise<Array>} Array of team objects
 * @throws {Error} If API request fails
 */
async function fetchUserTeams(userId) {
  // Implementation
}
```

### README Updates

Update `README.md` when adding:
- New dependencies
- Environment variables
- Setup steps
- API changes

---

## 🚨 Emergency Procedures

### Hotfix Process

**If critical bug found in `master`:**

```bash
# 1. Create hotfix directly on master
git checkout master
git pull origin master

# 2. Fix bug quickly
# ... make changes ...
git add .
git commit -m "hotfix: critical bug in payment processing"
git push origin master

# 3. Notify team
# Post in team chat about hotfix
```

### Rollback Process

**If deployment fails:**

```bash
# 1. Revert to previous tag
git checkout sprint-XX-release
git push origin master --force

# 2. Investigate issue on master
# Fix issue, test thoroughly

# 3. Re-deploy when ready
```

---

## 📋 Checklist for New Developers

### First Day Setup

- [ ] Clone repository
- [ ] Install all dependencies (Python, Node, PostgreSQL, Redis)
- [ ] Setup virtual environment
- [ ] Run migrations
- [ ] Create superuser
- [ ] Run development server (verify works)
- [ ] Run tests (verify all passing)
- [ ] Read sprint documentation
- [ ] Join team communication channels
- [ ] Setup IDE with recommended extensions
- [ ] Review this development guidelines document

### Before First Commit

- [ ] Understand single-branch workflow
- [ ] Configure git user name and email
- [ ] Setup git commit message template
- [ ] Test commit and push permissions
- [ ] Review code standards
- [ ] Understand Definition of Done
- [ ] Know who to ask for help

---

## 🎓 Learning Resources

### Django
- [Django Documentation](https://docs.djangoproject.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [Test-Driven Development with Python](https://www.obeythetestinggoat.com/)

### Frontend
- [HTMX Documentation](https://htmx.org/docs/)
- [Alpine.js](https://alpinejs.dev/)
- [Modern JavaScript](https://javascript.info/)

### Testing
- [pytest Documentation](https://docs.pytest.org/)
- [Playwright](https://playwright.dev/)
- [Testing Library](https://testing-library.com/)

### Git
- [Git Best Practices](https://www.git-scm.com/book/en/v2)
- [Conventional Commits](https://www.conventionalcommits.org/)

---

## ✅ Summary

**Key Takeaways:**

1. **One Branch:** All development on `development` branch
2. **Frequent Commits:** Push multiple times per day
3. **Communication:** Daily standups, announce file edits
4. **Quality:** Tests, linting, coverage before commit
5. **Standards:** Follow code style guides strictly
6. **Collaboration:** Help teammates, resolve conflicts together

**Success Formula:**

```
Single Branch + Frequent Commits + Daily Communication + High Quality = Successful Build
```

---

**Questions?** Ask in team chat or during daily standup.

**Document Version:** 1.0  
**Last Updated:** November 4, 2025  
**Next Review:** End of Sprint 4 (December 2025)

---

**Happy Coding! 🚀**
