from typing import Optional

from popget.__about__ import __version__


CLIENT_DEFAULT_USER_AGENT = 'popget/{}'.format(__version__)

CLIENT_TIMEOUT = None  # type: Optional[float]

CLIENT_DISABLE_VERIFY_SSL = False
