# Pull Request

## Description
<!-- Provide a clear and concise description of your changes -->

## Type of Change
<!-- Mark the relevant option with an "x" -->

- [ ] 🐛 Bug fix (non-breaking change which fixes an issue)
- [ ] ✨ New feature (non-breaking change which adds functionality)
- [ ] 💥 Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] 📝 Documentation update
- [ ] 🔧 Configuration change
- [ ] ♻️ Code refactoring
- [ ] 🎨 UI/UX improvement
- [ ] ⚡ Performance improvement
- [ ] 🧪 Test addition or update
- [ ] 🔒 Security fix

## Related Issues
<!-- Link related issues using #issue_number -->

Fixes #
Related to #

## Changes Made
<!-- List the main changes in bullet points -->

- 
- 
- 

## Testing
<!-- Describe the tests you ran to verify your changes -->

### Test Configuration
- **Python Version**: 3.11
- **Django Version**: 4.2.7
- **Database**: PostgreSQL 15

### Tests Performed
- [ ] Unit tests pass (`pytest`)
- [ ] Integration tests pass
- [ ] Manual testing completed
- [ ] All existing tests pass

### Test Coverage
<!-- If applicable, include test coverage information -->
- Coverage before: X%
- Coverage after: Y%

## Screenshots/Videos
<!-- If applicable, add screenshots or videos to demonstrate the changes -->

## Checklist
<!-- Mark completed items with an "x" -->

### Code Quality
- [ ] My code follows the project's style guidelines
- [ ] I have performed a self-review of my own code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] My changes generate no new warnings or errors
- [ ] I have removed any console.log or debug statements

### Testing
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes
- [ ] I have tested the changes in development environment
- [ ] I have tested edge cases and error scenarios

### Documentation
- [ ] I have updated the documentation accordingly
- [ ] I have updated the API documentation if API changes were made
- [ ] I have updated the README.md if needed
- [ ] I have added docstrings to new functions/classes

### Database
- [ ] I have created necessary migrations (`python manage.py makemigrations`)
- [ ] I have tested migrations are reversible (`python manage.py migrate` and rollback)
- [ ] I have updated the database schema documentation if needed
- [ ] No sensitive data is included in migrations

### Security
- [ ] I have checked for security vulnerabilities
- [ ] No sensitive information (API keys, passwords, tokens) is committed
- [ ] I have validated and sanitized all user inputs
- [ ] I have implemented proper authentication/authorization checks

### Dependencies
- [ ] I have updated `requirements.txt` if new packages were added
- [ ] I have documented why new dependencies are needed
- [ ] Dependencies are pinned to specific versions
- [ ] No conflicting dependencies

### Performance
- [ ] I have checked for N+1 queries
- [ ] I have added database indexes where needed
- [ ] I have optimized queries using `select_related()` or `prefetch_related()`
- [ ] I have tested performance impact of changes

## Deployment Notes
<!-- Add any special deployment instructions or notes -->

### Pre-deployment
<!-- Things to do before deploying -->
- [ ] Run migrations: `python manage.py migrate`
- [ ] Update environment variables (list below)
- [ ] Clear cache if needed

### Post-deployment
<!-- Things to verify after deploying -->
- [ ] Verify feature works in production
- [ ] Check error logs
- [ ] Monitor performance metrics

### Environment Variables
<!-- List any new or modified environment variables -->
```
VARIABLE_NAME=description_of_value
```

## Rollback Plan
<!-- Describe how to rollback these changes if needed -->

## Additional Notes
<!-- Add any additional information that reviewers should know -->

## Reviewer Notes
<!-- @mentions for specific reviewers or teams -->

/cc @reviewer1 @reviewer2

---

**Sprint**: [Sprint Number]
**Story Points**: [Points]
**Ticket**: [Ticket ID]
