popget
======

|Build Status|

.. |Build Status| image:: https://circleci.com/gh/depop/popget.svg?style=shield&circle-token=66ab09119c495365d662fe170e5efcc4467e3b37
    :alt: Build Status

A simple no-bells-and-whistles REST-API client, optionally supporting async requests.

We use this for service-to-service requests in our heterogenous
microservices environment.

Usage
-----

Configuration
~~~~~~~~~~~~~

Settings are intended to be configured primarily via a python file, such
as your existing Django ``settings.py`` or Celery ``celeryconfig.py``.
To bootstrap this, there are a couple of env vars to control how config
is loaded:

-  ``POPGET_APP_CONFIG``
   should be an import path to a python module, for example:
   ``POPGET_APP_CONFIG=django.conf.settings``
-  ``POPGET_CONFIG_NAMESPACE``
   Sets the prefix used for loading further config values from env and
   config file. Defaults to ``POPGET``.

See source of ``popget/conf/defaults.py`` for more details.

Some useful config keys (all of which are prefixed with
``POPGET_`` by default):

-  ``CLIENT_DEFAULT_USER_AGENT`` when making requests, popget will use this
   string as the user agent.
-  ``CLIENT_TIMEOUT`` if ``None`` then no timeout, otherwise this timeout
   (in seconds) will be applied to all requests. Requests which timeout will
   return a 504 response, which will be raised as an ``HTTPError``.

APIClient
~~~~~~~~~

You will sub-class ``APIClient`` to make your API. You do not need to
instantiate the client, all methods are class-methods.

eg

.. code:: python

    from popget import APIClient, GetEndpoint

    class ThingServiceClient(APIClient):

        class Config:
            base_url = 'http://things.depop.com'

        get_things = GetEndpoint(
            '/things/{user_id}/',  # url format string
            Arg('type', required=True),  # required querystring param (validated on call)
        )

Results in a client method you can call like:

.. code:: python

    data = ThingServiceClient.get_things(user_id=2345, type='cat')

Which will perform a request like:

.. code:: bash

    GET http://things.depop.com/things/2345/?type=cat

If response was ``"Content-Type: application/json"`` then ``data`` is
already deserialized.

Under Python 3 there is a further distinction between ``str`` and ``bytes``.
If the Content-Type header contains ``text/`` then the returned value
will be encoded to ``str`` (by underlying ``python-requests`` lib).
Other content types will return ``bytes``.

We use ``raise_for_status`` so anything >= 400 will raise a ``requests.HTTPError``.

APIEndpoint
~~~~~~~~~~~

``APIEndpoint`` is the base class for endpoint methods. ``GetEndpoint``,
``PostEndpoint``, ``PutEndpoint``, ``PatchEndpoint`` and ``DeleteEndpoint``
are provided for convenience, allowing to omit the method arg.

Params from url path (format string), querystring and request headers
(format string of value portion) will be extracted and made available
as kwargs on the resulting callable method on your client class.

This means arg names must be unique across all three sources of args.
This is feasible because path and header args can be freely chosen when
implementing the client (they are just format string identifiers rather
than part of the REST API itself like querystring args are).

e.g.

.. code:: python

    from popget import APIClient, Arg, GetEndpoint

    class ThingServiceClient(APIClient):

        class Config:
            base_url = 'http://things.depop.com'

        get_things = GetEndpoint(
            '/things/{user_id}/',  # url (format string)
            querystring_args=(
                Arg('type', required=True),
                Arg('offset_id'),
                Arg('limit', default=25),
            ),
            request_headers={      # added to all requests
                'Authorization': 'Bearer {access_token}'  # (format string)
            }
        )

This will give you a client with a ``get_things`` method you can call like:

.. code:: python

    response_data = ThingServiceClient.get_things(
        user_id=123,
        type='cat',
        offset_id='65345ff34e344ab53c',
        limit=20,
        access_token='87a64c98b62d39e8625f',
    )

Querystring args can have a callable as the default value, e.g.:

.. code:: python

    from datetime import datetime
    from popget import APIClient, Arg, GetEndpoint

    def now():
        return datetime.now().isoformat()

    class ThingServiceClient(APIClient):

        class Config:
            base_url = 'http://things.depop.com'

        get_things = GetEndpoint(
            '/things/{user_id}/',  # url (format string)
            querystring_args=(
                Arg('since', default=now),
            ),
            request_headers={      # added to all requests
                'Authorization': 'Bearer {access_token}'  # (format string)
            }
        )

    response_data = ThingServiceClient.get_things(user_id=123)
    # GET http://things.depop.com/things/123/?since=2018-02-09T13:31:10.569481

You can still pass extra args down into the ``requests`` lib on a per-call
basis by using ``_request_kwargs``:

.. code:: python

    response_data = ThingServiceClient.get_things(
        user_id=123,
        type='cat',
        offset_id='65345ff34e344ab53c',
        limit=20,
        access_token='87a64c98b62d39e8625f',
        _request_kwargs={
            'headers': {
                'X-Depop-WTF': 'something something'
            }
        },
    )

And for calls with a request body:

.. code:: python

    from popget import APIClient, PostEndpoint, BodyType

    class ThingServiceClient(APIClient):

        class Config:
            base_url = 'http://things.depop.com'

        new_thing = PostEndpoint(
            '/things/',
            body_required=True,
            body_type=BodyType.FORM_ENCODED,
            request_headers={
                'Authorization': 'Bearer {access_token}',
                'Content-Type': 'application/json; charset=utf-8'
            }
        )

    response_data = ThingServiceClient.new_thing(
        access_token='87a64c98b62d39e8625f',
        body={
            'type': 'dog',
            'name': 'fido',
        }
    )

You can also pass a custom ``requests.Session`` instance on a per-request basis using the ``_session`` kwarg:

.. code:: python

    from django.conf import settings
    from requests_oauthlib import OAuth1Session

    from myproject.twitter.client import TwitterClient

    def tweet_from(user, message, **extra):
        oauth_session = OAuth1Session(
            settings.TWITTER_CONSUMER_KEY,
            client_secret=settings.TWITTER_CONSUMER_SECRET,
            resource_owner_key=user.tw_access_token,
            resource_owner_secret=user.tw_access_token_secret,
        )
        body = {
            'status': message,
        }
        body.update(extra)
        return TwitterClient.update_status(body=body, _session=oauth_session)


Asynchronous
~~~~~~~~~~~~

Optional support for asynchronous requests is provided, via a ``requests-futures`` backend.

``pip install popget[threadpool]``

An async variant of the ``APIClient`` is provided which will have both async and blocking
versions of all endpoint methods.

.. code:: python

    from popget import Arg, GetEndpoint
    from popget.async.threadpool import APIClient
    import requests

    class ThingServiceClient(APIClient):

        class Config:
            base_url = 'http://things.depop.com'

        get_things = GetEndpoint(
            '/things/{user_id}/',            # url format string
            querystring_args=(
                Arg('type', required=True),  # required querystring param (validated on call)
            ),
        )

    # blocking:
    data = ThingServiceClient.get_things(user_id=2345, type='cat')

    # async:
    future = ThingServiceClient.async_get_things(user_id=2345, type='cat')
    # response is parsed and may raise, as for blocking requests
    try:
        data = future.result()
    except requests.exceptions.HTTPError as e:
        print(repr(e))

The async endpoint methods will return a standard ``concurrent.futures.Future`` object.

See `Python docs <https://docs.python.org/dev/library/concurrent.futures.html>`_.

You can customise the name of the generated async endpoint methods:

.. code:: python

    class ThingServiceClient(APIClient):

        class Config:
            base_url = 'http://things.depop.com'
            async_method_template = '{}__async'

        get_things = GetEndpoint(
            '/things/{user_id}/',            # url format string
            querystring_args=(
                Arg('type', required=True),  # required querystring param (validated on call)
            ),
        )

    future = ThingServiceClient.get_things__async(user_id=2345, type='cat')


Compatibility
-------------

This project is tested against:

=========== ===
Python 2.7   * 
Python 3.6   * 
=========== ===

Running the tests
-----------------

CircleCI
~~~~~~~~

| The easiest way to test the full version matrix is to install the
  CircleCI command line app:
| https://circleci.com/docs/2.0/local-jobs/
| (requires Docker)

The cli does not support 'workflows' at the moment so you have to run
the two Python version jobs separately:

.. code:: bash

    circleci build --job python-2.7

.. code:: bash

    circleci build --job python-3.6

py.test (single python version)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

It's also possible to run the tests locally, allowing for debugging of
errors that occur.

Decide which Python version you want to test and create a virtualenv:

.. code:: bash

    pyenv virtualenv 3.6.3 popget
    pip install -r requirements-test.txt
    py.test -v -s --ipdb tests/
