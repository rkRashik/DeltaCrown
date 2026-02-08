"""
Notification services package.

MILESTONE F: Services for notification delivery
- webhook_service: HTTP webhook delivery with HMAC signing and retries
- Re-exports notify() and emit() from parent services.py for backward compatibility
"""

# Import notify and emit from the parent services.py file (not this package)
import importlib.util
import os

services_py_path = os.path.join(os.path.dirname(__file__), '..', 'services.py')
spec = importlib.util.spec_from_file_location("notification_services_module", services_py_path)
services_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(services_module)

notify = services_module.notify
emit = services_module.emit
NotificationService = services_module.NotificationService

# Import webhook services from this package
from .webhook_service import (
    WebhookService,
    get_webhook_service,
    deliver_webhook,
)

__all__ = [
    'notify',
    'emit',
    'NotificationService',
    'WebhookService',
    'get_webhook_service',
    'deliver_webhook',
]
