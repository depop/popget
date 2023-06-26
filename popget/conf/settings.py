from popget.__about__ import __version__

try:
    from django.conf import settings
except ImportError:
    settings = None

CLIENT_DEFAULT_USER_AGENT: str = getattr(
    settings, 'POPGET_CLIENT_DEFAULT_USER_AGENT', 'popget/{}'.format(__version__)
)

CLIENT_DEFAULT_HEADERS: dict[str, str] = getattr(
    settings, 'POPGET_CLIENT_DEFAULT_HEADERS', {}
)

CLIENT_TIMEOUT: float = getattr(settings, 'POPGET_CLIENT_TIMEOUT', 3.0)

CLIENT_DISABLE_VERIFY_SSL: bool = getattr(settings, 'POPGET_CLIENT_DISABLE_VERIFY_SSL', False)
