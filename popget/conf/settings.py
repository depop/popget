from popget.__about__ import __version__

try:
    from django.conf import settings
except ImportError:
    settings = None

CLIENT_DEFAULT_USER_AGENT = getattr(
    settings, 'POPGET_CLIENT_DEFAULT_USER_AGENT', 'popget/{}'.format(__version__)
)

CLIENT_TIMEOUT = getattr(settings, 'POPGET_CLIENT_TIMEOUT', None)  # type: float | None

CLIENT_DISABLE_VERIFY_SSL = getattr(settings, 'POPGET_CLIENT_DISABLE_VERIFY_SSL', False)
