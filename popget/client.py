import string
from six import add_metaclass, string_types
from typing import Any, Callable, Dict, Optional, Set, Type, Union  # noqa

import requests
from requests.exceptions import Timeout

from popget.conf import settings
from popget.extratypes import ResponseTypes  # noqa
from popget.utils import update_nested


JSON = 'json'

FORM_ENCODED = 'data'


class MissingRequiredArg(TypeError):
    pass


class ArgNameConflict(ValueError):
    pass


def _validate_arg_name(arg, arg_type, reserved):
    """
    Validate that `arg` does not conflict with names already defined in
    `reserved`.

    Kwargs:
        arg (str): the arg name to validate
        arg_type (str): a description for the arg type, to use in exception
            message if conflicting
        reserved (Set[str]): reserved arg names

    Returns:
        str: validated arg name
    """
    if arg in reserved:
        raise ArgNameConflict(
            '{arg_type} arg `{arg}` conflicts with a reserved arg name.'.format(
                arg_type=arg_type,
                arg=arg,
            )
        )
    return arg


class APIEndpoint(object):
    """
    Params from url path (format string), querystring and request headers
    (format string of value portion) will be extracted and made available
    as kwargs on the resulting method call.

    This means arg names must be unique across all three sources of args.
    This is feasible because path and header args can be freely chosen when
    implementing the client (they are just format string identifiers rather
    than part of the REST API itself like querystring args are).

    e.g.

        class ThingServiceClient(APIClient):

            get_things = APIEndpoint(
                'GET',
                '/things/{user_id}/',  # url format string
                querystring_args=(
                    ('type', True),  # required arg
                    'offset_id',
                    'limit',
                ),
                request_headers={
                    'Authorization': 'Bearer {access_token}'
                }
            )

    This will give you a client with a `get_things` method you can call like:

        response_data = ThingServiceClient.get_things(
            user_id=123,
            type='cat',
            offset_id='65345ff34e344ab53c',
            limit=20,
            access_token='87a64c98b62d39e8625f',
        )

    You can still pass extra args down into the `requests` lib on a per-call
    basis by using `_request_kwargs`:

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

        class ThingServiceClient(APIClient):

            new_thing = APIEndpoint(
                'POST',
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
    """

    RESERVED_NAMES = ('_request_kwargs',)

    method = None  # type: str
    path = None  # type: str

    body_type = None  # type: str
    body_arg = None  # type: str

    request_headers = None  # type: Optional[Dict[str, str]]

    required_args = None  # type: Set[str]
    url_args = None  # type: Set[str]
    querystring_args = None  # type: Set[str]
    request_header_args = None  # type: Dict[str, Set[str]]

    def __init__(self, method, path, querystring_args=None, request_headers=None,
                 body_type=JSON, body_arg='body', body_required=False):
        """
        Kwargs:
            method (str): 'GET', 'POST' etc
            path (str): path portion of url (appended to `APIClient.base_url`)
            querystring_args (Optional[Tuple[Union[Tuple[str, bool], str]]]):
                if given, tuple of non-required arg names, or (<arg name>, True)
                for required args
            request_headers (Optional[Dict[str, str]]): if given, a dict of
                request headers which will be applied to all requests
            body_type (str): which kwarg in `requests` lib to use for request
                body, e.g. "data" for form-encoded or "json" for JSON encoded
                (in both cases just pass a python dict in the call)
            body_arg (str): `body_arg` will be made available as a kwarg in the
                resulting client method, as such it needs a unique name. If the
                default name, "body", is needed as a querystring arg then
                specify a custom arg name here.
        """
        f = string.Formatter()

        reserved = set(self.RESERVED_NAMES)
        all_args = set()
        required_args = set()

        # request body arg
        all_args.add(
            _validate_arg_name(body_arg, '`body_arg`', reserved)
        )
        reserved.add(body_arg)
        if body_required:
            required_args.add(body_arg)

        # parse url args
        url_args = set()
        for tokens in f.parse(path):
            if tokens[1] is not None:
                all_args.add(
                    _validate_arg_name(tokens[1], 'Url', reserved)
                )
                url_args.add(tokens[1])
                required_args.add(tokens[1])  # all url args are required

        # parse querystring args
        querystring_args_ = set()
        if querystring_args is not None:
            for arg in querystring_args:
                if isinstance(arg, string_types):
                    required = False
                else:
                    arg, required = arg
                all_args.add(
                    _validate_arg_name(arg, 'Querystring', reserved)
                )
                if required:
                    required_args.add(arg)
                querystring_args_.add(arg)

        # parse request-header args
        request_header_args = {}
        if request_headers is not None:
            for header, value in request_headers.items():
                for tokens in f.parse(value):
                    if tokens[1] is not None:
                        all_args.add(
                            _validate_arg_name(tokens[1], 'Request-header', reserved)
                        )
                        request_header_args.setdefault(header, set()).add(tokens[1])
                        required_args.add(tokens[1])  # all request-header args are required

        self.method = method.lower()
        self.path = path

        self.body_type = body_type
        self.body_arg = body_arg

        self.request_headers = request_headers

        self.required_args = required_args
        self.url_args = url_args
        self.querystring_args = querystring_args_
        self.request_header_args = request_header_args


class GetEndpoint(APIEndpoint):

    def __init__(self, *args, **kwargs):
        super(GetEndpoint, self).__init__('GET', *args, **kwargs)


class PostEndpoint(APIEndpoint):

    def __init__(self, *args, **kwargs):
        super(PostEndpoint, self).__init__('POST', *args, **kwargs)


class PatchEndpoint(APIEndpoint):

    def __init__(self, *args, **kwargs):
        super(PatchEndpoint, self).__init__('PATCH', *args, **kwargs)


class PutEndpoint(APIEndpoint):

    def __init__(self, *args, **kwargs):
        super(PutEndpoint, self).__init__('PUT', *args, **kwargs)


class DeleteEndpoint(APIEndpoint):

    def __init__(self, *args, **kwargs):
        super(DeleteEndpoint, self).__init__('DELETE', *args, **kwargs)


def method_factory(endpoint):
    # type: (APIEndpoint) -> Callable[[Any], ResponseTypes]
    """
    Kwargs:
        endpoint: the endpoint to generate a callable method for

    Returns:
        A classmethod to be attached to the APIClient, which will perform
        the actual request for this particular endpoint.
        In turn the method returns response content, either string or
        deserialized JSON data.
    """
    def client_method(cls, _request_kwargs=None, **call_kwargs):
        # type: (Type[APIClient], Optional[Dict], **object) -> ResponseTypes
        """
        Kwargs:
            _request_kwargs (dict): extra kwargs to pass into the underlying
                `requests` lib method
            **call_kwargs: expected args for the endpoint (url, querystring,
                request-headers etc)

        Returns:
            Union[str, dict]: response content, either string or deserialized
            JSON data if response had 'application/json' content-type header.
        """
        for required in endpoint.required_args:
            if required not in call_kwargs:
                raise MissingRequiredArg('`{}` arg is required.'.format(required))

        # prepare url kwargs
        url_args = {
            arg: call_kwargs[arg]
            for arg in endpoint.url_args
        }

        # prepare querystring args
        querystring_args = {}
        for arg in endpoint.querystring_args:
            try:
                querystring_args[arg] = call_kwargs[arg]
            except KeyError:
                # non-required arg
                continue

        # prepare request-header args
        request_headers = {}
        for header, args in endpoint.request_header_args.items():
            header_kwargs = {
                arg: call_kwargs[arg]
                for arg in args
            }
            request_headers[header] = endpoint.request_headers[header].format(**header_kwargs)

        url_template = '{base_url}/{path}'.format(
            base_url=cls.base_url.rstrip('/'),
            path=endpoint.path.lstrip('/'),
        )
        url = url_template.format(**url_args)

        request_kwargs = {
            'params': querystring_args,
            'headers': request_headers,
        }

        request_body = call_kwargs.get(endpoint.body_arg)
        if request_body is not None:
            request_kwargs[endpoint.body_type] = request_body

        if _request_kwargs is not None:
            update_nested(request_kwargs, _request_kwargs)

        return cls._make_request(endpoint.method, url, **request_kwargs)

    return client_method


class APIClientMetaclass(type):
    """
    Makes API call methods from APIEndpoint definitions on the APIClient class

    (this 'metaclass magic' is similar to Django Model class where fields are
    defined on the class, and transformed by the metaclass into usable attrs)

    eg

        class ThingServiceClient(APIClient):

            base_url = 'http://things.depop.com'

            get_things = GetEndpoint(
                '/things/{user_id}/',  # url format string
                (('type', True),),     # required querystring param (validated on call)
            )

    Results in a client method you can call like:

        data = MyAPI.get_things(user_id=2345, type='cat')

    Which will perform a request like:

        GET http://things.depop.com/things/2345/?type=cat

    If response was "Content-Type: application/json" then `data` is already deserialized.

    We use `raise_for_status` so anything >= 400 will raise a `requests.HTTPError`.
    """

    def __new__(cls, name, bases, attrs):
        methods = {}
        attr_list = list(attrs.items())
        for name, endpoint in attr_list:
            if not isinstance(endpoint, APIEndpoint):
                continue
            methods[name] = classmethod(method_factory(endpoint))
            del attrs[name]
        attrs.update(methods)
        session = requests.Session()
        session.headers['User-Agent'] = settings.CLIENT_DEFAULT_USER_AGENT
        attrs['_r'] = session
        return type.__new__(cls, name, bases, attrs)


def get_response_body(response):
    # type: (requests.Response) -> ResponseTypes
    """
    Kwargs:
        response: from requests lib

    Returns:
        response content - either string or deserialized JSON data if response
        had 'application/json' content type header.
    """

    if response.status_code == 204:
        return None

    try:
        # Requests uses a 'dict-like' case-insensitive dict, but the case-
        # insensitivity only applies to __getitem__ and not .get()
        # So we can't use .get() here but should catch the KeyError.
        content_type = response.headers['Content-Type']
    except KeyError:
        content_type = ''

    if 'application/json' in content_type:
        return response.json()  # JSONTypes
    elif 'text/' in content_type:
        return response.text  # str
    else:
        return response.content  # bytes


@add_metaclass(APIClientMetaclass)
class APIClient(object):

    base_url = ''
    _r = None  # type: requests.Session

    @classmethod
    def _add_timeout_and_handle(cls, method, url, *args, **kwargs):
        # type: (str, str, *Any, **Any) -> requests.Response

        # all requests should contain a default timeout value
        if kwargs.get('timeout') is None:
            kwargs['timeout'] = settings.CLIENT_TIMEOUT

        try:
            res = getattr(cls._r, method)(url, *args, **kwargs)
        except Timeout as e:
            res = requests.Response()
            res.request = e.request
            res.url = url
            res.reason = str(e)
            res.status_code = 504

        return res

    @classmethod
    def _make_request(cls, method, url, *args, **kwargs):
        # type: (str, str, *Any, **Any) -> ResponseTypes
        """
        Don't call this directly. Instead, add APIEndpoint instances to your
        APIClient sub-class definition. Accessor methods will be generated by
        the APIClientMetaclass magic.

        Kwargs:
            method: name of a method on the `requests` lib, such as 'get'
            url: url of endpoint to call, with all params substituted in
            *args
            **kargs
                passed through to underlying `requests` method

        Returns:
            response content, either string or deserialized JSON data if
            response had 'application/json' content type header.
        """
        if settings.CLIENT_DISABLE_VERIFY_SSL:
            kwargs['verify'] = False

        res = cls._add_timeout_and_handle(method, url, *args, **kwargs)

        res.raise_for_status()
        return get_response_body(res)
