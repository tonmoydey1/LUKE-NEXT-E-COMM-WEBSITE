from .base import *  # noqa

DEBUG = True
if not EMAIL_HOST_USER or not EMAIL_HOST_PASSWORD:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
