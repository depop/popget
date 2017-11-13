popget
======

|Build Status|

.. |Build Status| image:: https://circleci.com/gh/depop/popget.svg?style=shield&circle-token=66ab09119c495365d662fe170e5efcc4467e3b37
    :alt: Build Status

A simple no-bells-and-whistles REST-API client.

We use this for service--to-service requests in our heterogenous
microservices environment.

Usage
-----

APIClient
~~~~~~~~~

You will sub-class ``APIClient`` to make your API. You do not need to
instantiate the client, all methods are class-methods.

eg

.. code:: python

    from popget.client import APIClient, GetEndpoint

    class ThingServiceClient(APIClient):

        base_url = 'http://things.depop.com'

        get_things = GetEndpoint(
            '/things/{user_id}/',  # url format string
            (('type', True),),     # required querystring param (validated on call)
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

    from popget.client import APIClient, APIEndpoint

    class ThingServiceClient(APIClient):

        get_things = APIEndpoint(
            'GET',
            '/things/{user_id}/',  # url (format string)
            querystring_args=(
                ('type', True),    # required arg
                'offset_id',       # non-required args
                'limit',
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

    from popget.client import APIClient, PostEndpoint, FORM_ENCODED

    class ThingServiceClient(APIClient):

        new_thing = PostEndpoint(
            '/things/',
            body_required=True,
            body_type=FORM_ENCODED,
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
