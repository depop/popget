import os
from typing import Optional

from popget.__about__ import __version__


# namespace for config keys loaded from e.g. Django conf or env vars
CONFIG_NAMESPACE = os.getenv('POPGET_CONFIG_NAMESPACE', 'POPGET')

# optional import path to file containing namespaced config (e.g. 'django.conf.settings')
APP_CONFIG = os.getenv('POPGET_APP_CONFIG', None)


CLIENT_DEFAULT_USER_AGENT = 'popget/{}'.format(__version__)

CLIENT_TIMEOUT = None  # type: Optional[float]

CLIENT_DISABLE_VERIFY_SSL = False
