# Contributing to DeltaCrown Tournament Engine

Thank you for your interest in contributing to DeltaCrown! This document provides guidelines and best practices for contributing to this project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Development Workflow](#development-workflow)
- [Code Standards](#code-standards)
- [Commit Messages](#commit-messages)
- [Pull Request Process](#pull-request-process)
- [Testing Guidelines](#testing-guidelines)
- [Documentation](#documentation)

## Code of Conduct

- Be respectful and inclusive
- Welcome newcomers and help them learn
- Focus on constructive feedback
- Keep discussions professional and on-topic

## Getting Started

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Git
- PostgreSQL 15 (via Docker)
- Redis 7 (via Docker)

### First-Time Setup

1. **Fork and Clone**
   ```bash
   git clone https://github.com/rkRashik/DeltaCrown.git
   cd DeltaCrown
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

4. **Environment Configuration**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Start Docker Services**
   ```bash
   docker-compose up -d postgres redis
   ```

6. **Run Migrations**
   ```bash
   python manage.py migrate
   ```

7. **Create Superuser**
   ```bash
   python manage.py createsuperuser
   ```

8. **Run Development Server**
   ```bash
   python manage.py runserver
   ```

## Development Setup

### Branch Strategy

**We use a single master branch workflow:**
- All development happens on `master`
- No feature branches
- Commit frequently with detailed messages
- Each commit should be atomic and well-tested

### Development Environment

```bash
# Use development settings
export DJANGO_SETTINGS_MODULE=deltacrown.settings.development

# Or in your .env file
DJANGO_SETTINGS_MODULE=deltacrown.settings.development
```

## Development Workflow

### 1. Update Your Local Repository

```bash
git pull origin master
```

### 2. Make Your Changes

- Write clean, readable code
- Follow the project's code style
- Add tests for new functionality
- Update documentation as needed

### 3. Test Your Changes

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_authentication.py

# Run with coverage
pytest --cov=apps --cov-report=html
```

### 4. Commit Your Changes

```bash
git add .
git commit -m "feat(auth): add email verification"
```

### 5. Push to Master

```bash
git push origin master
```

## Code Standards

### Python Style Guide

We follow **PEP 8** with some modifications:

- **Line length**: 100 characters (not 79)
- **Indentation**: 4 spaces
- **Quotes**: Double quotes for strings
- **Imports**: Organized with isort

### Code Formatting Tools

We use automated code quality tools to maintain consistent code style. All tools are configured in `pyproject.toml`, `.flake8`, and `.pylintrc`.

#### Installation

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Install pre-commit hooks (RECOMMENDED)
pre-commit install
```

#### Manual Tool Usage

```bash
# Format code with black (auto-fixes)
black apps/ deltacrown/ tests/

# Sort imports (auto-fixes)
isort apps/ deltacrown/ tests/

# Check code style
flake8 apps/ deltacrown/ tests/

# Advanced linting
pylint apps/ deltacrown/ tests/

# Type checking
mypy apps/ deltacrown/

# Run all checks at once
pre-commit run --all-files
```

#### Pre-commit Hooks (Automatic)

Once installed, pre-commit hooks automatically run on `git commit`:

- **black**: Code formatting
- **isort**: Import sorting
- **flake8**: Style guide enforcement
- **trailing-whitespace**: Remove trailing whitespace
- **end-of-file-fixer**: Ensure files end with newline
- **check-yaml**: YAML syntax validation
- **check-added-large-files**: Prevent large files (>500KB)
- **detect-secrets**: Scan for hardcoded secrets

To bypass hooks (not recommended):
```bash
git commit --no-verify
```

#### Code Quality Standards

- **Line Length**: 88 characters (black default)
- **Import Order**: stdlib → third-party → local (isort)
- **Docstrings**: Google style for all public functions/classes
- **Type Hints**: Required for all function signatures
- **Test Coverage**: Minimum 80% required
- **Cyclomatic Complexity**: Max 10 per function

#### Tool Configuration Files

| Tool | Configuration File | Purpose |
|------|-------------------|---------|
| black | `pyproject.toml` | Code formatting rules |
| isort | `pyproject.toml` | Import sorting rules |
| flake8 | `.flake8` | Style guide enforcement |
| pylint | `.pylintrc` | Advanced linting rules |
| mypy | `pyproject.toml` | Type checking configuration |
| pytest | `pytest.ini` | Test configuration |
| coverage | `pyproject.toml` | Coverage requirements |
| pre-commit | `.pre-commit-config.yaml` | Hook configuration |

#### CI/CD Integration

All code quality checks run automatically in GitHub Actions:

- **On Pull Request**: Runs full test suite + linting
- **On Push to Master**: Runs tests + builds Docker image
- **Code Quality Jobs**: black, isort, flake8, pylint, mypy, bandit, safety
- **Required**: All checks must pass before merge

See `.github/workflows/ci.yml` for complete CI pipeline configuration.

### Django Best Practices

1. **Models**
   ```python
   class Tournament(models.Model):
       """Tournament model representing esports tournaments."""
       
       name = models.CharField(max_length=200, help_text="Tournament name")
       
       class Meta:
           ordering = ["-created_at"]
           verbose_name = "Tournament"
           verbose_name_plural = "Tournaments"
       
       def __str__(self):
           return self.name
   ```

2. **Views**
   ```python
   from rest_framework import viewsets
   from rest_framework.permissions import IsAuthenticated
   
   class TournamentViewSet(viewsets.ModelViewSet):
       """
       ViewSet for managing tournaments.
       
       Provides CRUD operations for tournaments.
       """
       queryset = Tournament.objects.all()
       serializer_class = TournamentSerializer
       permission_classes = [IsAuthenticated]
   ```

3. **Serializers**
   ```python
   from rest_framework import serializers
   
   class TournamentSerializer(serializers.ModelSerializer):
       """Serializer for Tournament model."""
       
       class Meta:
           model = Tournament
           fields = "__all__"
           read_only_fields = ["id", "created_at", "updated_at"]
   ```

4. **Query Optimization**
   ```python
   # Use select_related for foreign keys
   tournaments = Tournament.objects.select_related("organizer").all()
   
   # Use prefetch_related for many-to-many
   tournaments = Tournament.objects.prefetch_related("teams").all()
   
   # Avoid N+1 queries
   tournaments = Tournament.objects.prefetch_related(
       "teams__players"
   ).all()
   ```

### API Design

- Use RESTful conventions
- Proper HTTP status codes
- Consistent response format
- Comprehensive error messages
- API versioning in URLs

### Security Guidelines

- Never commit sensitive data (.env files, secrets)
- Use Django's built-in protections (CSRF, XSS, SQL injection)
- Validate all user inputs
- Use permissions and authentication
- Sanitize data before displaying

## Commit Messages

We follow **Conventional Commits** specification:

### Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, no logic change)
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `test`: Adding or updating tests
- `chore`: Maintenance tasks
- `ci`: CI/CD changes
- `build`: Build system changes

### Examples

```bash
# Simple feature
git commit -m "feat(auth): add JWT token refresh endpoint"

# Bug fix with detailed description
git commit -m "fix(tournaments): resolve duplicate registration issue

- Added unique constraint on (tournament, team) combination
- Added validation in serializer
- Updated tests to cover edge cases

Fixes #123"

# Breaking change
git commit -m "feat(api): change user registration endpoint

BREAKING CHANGE: Registration now requires email verification.
Clients must implement email verification flow."
```

### Commit Guidelines

- **One logical change per commit**
- **Present tense**: "add feature" not "added feature"
- **Imperative mood**: "fix bug" not "fixes bug"
- **Lowercase subject**: except for proper nouns
- **No period at the end** of subject line
- **Body explains what and why**, not how
- **Reference issues** in footer

## Pull Request Process

### Creating a Pull Request

1. **Ensure all tests pass**
   ```bash
   pytest
   flake8
   mypy apps/
   ```

2. **Update documentation**
   - Update README.md if needed
   - Add/update API documentation
   - Update changelog

3. **Fill out PR template completely**
   - Clear description
   - List all changes
   - Reference related issues
   - Add screenshots if UI changes

4. **Request review**
   - Assign appropriate reviewers
   - Address all comments
   - Re-request review after changes

### PR Review Checklist

**For Authors:**
- [ ] All tests pass
- [ ] Code follows style guide
- [ ] Documentation updated
- [ ] No debugging code left
- [ ] No sensitive data committed
- [ ] Migrations created and tested
- [ ] Performance impact considered

**For Reviewers:**
- [ ] Code is clear and maintainable
- [ ] Tests are comprehensive
- [ ] No security vulnerabilities
- [ ] Performance is acceptable
- [ ] Documentation is complete
- [ ] Breaking changes are documented

## Testing Guidelines

### Test Organization

```
tests/
├── conftest.py              # Pytest fixtures
├── factories.py             # Factory Boy factories
├── test_authentication.py   # Auth tests
├── test_tournaments.py      # Tournament tests
└── integration/             # Integration tests
    └── test_tournament_flow.py
```

### Writing Tests

```python
import pytest
from apps.accounts.models import User
from tests.factories import UserFactory

@pytest.mark.django_db
class TestUserAuthentication:
    """Test suite for user authentication."""
    
    def test_user_registration(self, api_client):
        """Test user can register with valid data."""
        data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "TestPass123!",
            "password_confirm": "TestPass123!",
        }
        response = api_client.post("/api/auth/register/", data)
        assert response.status_code == 201
        assert User.objects.filter(username="testuser").exists()
    
    def test_duplicate_email_rejected(self, api_client):
        """Test registration fails with duplicate email."""
        UserFactory(email="test@example.com")
        data = {
            "username": "newuser",
            "email": "test@example.com",
            "password": "TestPass123!",
            "password_confirm": "TestPass123!",
        }
        response = api_client.post("/api/auth/register/", data)
        assert response.status_code == 400
```

### Test Coverage

- Aim for **>80% code coverage**
- Test happy paths and edge cases
- Test error handling
- Test permissions and authorization
- Test API endpoints thoroughly

### Running Tests

```bash
# All tests
pytest

# Specific file
pytest tests/test_authentication.py

# Specific test
pytest tests/test_authentication.py::TestUserAuthentication::test_user_registration

# With coverage
pytest --cov=apps --cov-report=html

# View coverage report
open htmlcov/index.html
```

## Documentation

### Code Documentation

```python
def register_user(username: str, email: str, password: str) -> User:
    """
    Register a new user account.
    
    Args:
        username: Unique username for the account
        email: User's email address
        password: Plain text password (will be hashed)
    
    Returns:
        User: The created user instance
    
    Raises:
        ValidationError: If username or email already exists
        ValueError: If password is too weak
    
    Example:
        >>> user = register_user("player1", "player@example.com", "SecurePass123!")
        >>> user.username
        'player1'
    """
    # Implementation
```

### API Documentation

- Document all endpoints in `API_DOCUMENTATION.md`
- Include request/response examples
- Document error responses
- Provide code examples in multiple languages

### README Updates

Keep README.md updated with:
- Installation instructions
- Configuration options
- API overview
- Deployment guide
- Troubleshooting

## Questions?

- Open a [Discussion](https://github.com/rkRashik/DeltaCrown/discussions)
- Check existing [Issues](https://github.com/rkRashik/DeltaCrown/issues)
- Review [Documentation](./README.md)

---

**Thank you for contributing to DeltaCrown!** 🎮🏆
