from functools import partial
from six import add_metaclass
from typing import Any, Callable, Dict, Optional, Set, Tuple, Type, TypeVar, Union  # noqa

from mypy_extensions import Arg, DefaultArg, KwArg
import requests
from requests.exceptions import Timeout

from popget.conf import settings
from popget.endpoint import APIEndpoint, BodyType, BODY_CONTENT_TYPES, NO_DEFAULT
from popget.errors import MissingRequiredArg
from popget.extratypes import ResponseTypes  # noqa
from popget.utils import get_base_attr, update_nested


ClientMethod = Callable[
    [
        Arg(Type['APIClient'], 'cls'),
        DefaultArg(Optional[Dict[Any, Any]], '_request_kwargs'),
        DefaultArg(Optional[requests.Session], '_session'),
        KwArg(object),
    ],
    Union[ResponseTypes, object]
]


def method_factory(endpoint, client_method_name):
    # type: (APIEndpoint, str) -> ClientMethod
    """
    Kwargs:
        endpoint: the endpoint to generate a callable method for

    Returns:
        A classmethod to be attached to the APIClient, which will perform
        the actual request for this particular endpoint.
        In turn the method returns response content, either string or
        deserialized JSON data.
    """
    def _prepare_request(base_url, _request_kwargs=None, **call_kwargs):
        # type: (str, Optional[Dict], **Any) -> Tuple[str, Dict[str, Dict]]
        """
        Kwargs:
            base_url: base url of API
            _request_kwargs: extra kwargs to pass into the underlying
                `requests` lib method
            **call_kwargs: expected args for the endpoint (url, querystring,
                request-headers etc)
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
                querystring_args[arg.name] = call_kwargs[arg.name]
            except KeyError:
                # non-required arg
                if arg.default != NO_DEFAULT:
                    default = arg.default() if callable(arg.default) else arg.default
                    querystring_args[arg.name] = default

        # prepare request-header args
        request_headers = {}
        if endpoint.request_headers:
            request_headers.update(endpoint.request_headers)
        for header, args in endpoint.request_header_args.items():
            header_kwargs = {
                arg: call_kwargs[arg]
                for arg in args
            }
            request_headers[header] = request_headers[header].format(**header_kwargs)

        url_template = '{base_url}/{path}'.format(
            base_url=base_url.rstrip('/'),
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
            if 'Content-Type' not in request_kwargs['headers']:
                request_kwargs['headers']['Content-type'] = BODY_CONTENT_TYPES[BodyType(endpoint.body_type)]

        if _request_kwargs is not None:
            update_nested(request_kwargs, _request_kwargs)

        return url, request_kwargs

    def client_method(cls,  # type: Type[APIClient]
                      _request_kwargs=None,  # type: Optional[Dict]
                      _session=None,  # type: requests.Session
                      **call_kwargs
                      ):
        # type: (...) -> Union[ResponseTypes, object]
        """
        Returns:
            Response... for non-async clients this will be response content,
            either string or deserialized JSON data if response had
            'application/json' content-type header.
            For async clients this will be some type of future.
        """
        url, request_kwargs = _prepare_request(
            base_url=cls._config.base_url,
            _request_kwargs=_request_kwargs,
            **call_kwargs
        )
        client_method = getattr(cls, client_method_name)
        return client_method(endpoint.method, url, session=_session, **request_kwargs)

    return client_method


class ConfigClass(object):

    base_url = None  # type: str
    session_cls = None  # type: Type[requests.Session]
    _session = None  # type: requests.Session

    def __init__(self, config):
        self.base_url = getattr(config, 'base_url', '')
        self.session_cls = getattr(config, 'session_cls', requests.Session)

    @property
    def session(self):
        # type: () -> requests.Session
        if not self._session:
            session = self.session_cls()
            session.headers['User-Agent'] = settings.CLIENT_DEFAULT_USER_AGENT
            self._session = session
        return self._session


class APIClientMetaclass(type):
    """
    Makes API call methods from APIEndpoint definitions on the APIClient class

    (this 'metaclass magic' is similar to Django Model class where fields are
    defined on the class, and transformed by the metaclass into usable attrs)

    eg

        class ThingServiceClient(APIClient):

            class Config:
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

    config_class = ConfigClass

    @staticmethod
    def add_methods_for_endpoint(methods, name, endpoint, config):
        # type: (Dict[str, classmethod], str, APIEndpoint, Any) -> None
        methods[name] = classmethod(method_factory(endpoint, '_make_request'))

    def __new__(cls, name, bases, attrs):
        base_config = get_base_attr('Config', bases, attrs)
        attrs['_config'] = config = cls.config_class(base_config)

        methods = {}
        attr_list = list(attrs.items())
        for name, endpoint in attr_list:
            if not isinstance(endpoint, APIEndpoint):
                continue
            cls.add_methods_for_endpoint(methods, name, endpoint, config)
            del attrs[name]
        attrs.update(methods)
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

    _config = None  # type: ConfigClass

    @staticmethod
    def _request_kwargs(method, url, args, kwargs):
        # type: (str, str, Tuple[Any, ...], Dict[str, Any]) -> None

        if settings.CLIENT_DISABLE_VERIFY_SSL:
            kwargs['verify'] = False

        # all requests should contain a default timeout value
        if 'timeout' not in kwargs:
            kwargs['timeout'] = settings.CLIENT_TIMEOUT

    @staticmethod
    def handle(call, request_url):
        # type: (Callable[[], requests.Response], str) -> ResponseTypes

        try:
            res = call()
        except Timeout as e:
            # generate a proxy 504 'Gateway Timeout' response
            res = requests.Response()
            res.request = e.request
            res.url = request_url
            res.reason = str(e)
            res.status_code = 504

        res.raise_for_status()
        return get_response_body(res)

    @classmethod
    def _make_request(cls, method, url, session=None, *args, **kwargs):
        # type: (str, str, Optional[requests.Session], *Any, **Any) -> ResponseTypes
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
        cls._request_kwargs(method, url, args, kwargs)
        if session is None:
            session = cls._config.session
        call = partial(getattr(session, method), url, *args, **kwargs)
        return cls.handle(call, url)
