from django.test.runner import DiscoverRunner


class CustomTestRunner(DiscoverRunner):
    """
    Minimal custom test runner to satisfy settings.TEST_RUNNER.
    Delegates to Django's default DiscoverRunner.
    """
    pass

