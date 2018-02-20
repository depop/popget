import string
from typing import Any, Callable, Dict, Optional, Set, Tuple, Type, Union  # noqa

from enum import Enum  # via enum34 package on python 2.7

from popget.errors import ArgNameConflict
from popget.extratypes import ResponseTypes  # noqa


class BodyType(Enum):
    """
    `body_type` of requests which send a body

    NOTE:
    these enum values correspond to appropriate arg to request method
    e.g. requests.get(data={...})
    """
    JSON = 'json'
    FORM_ENCODED = 'data'


BODY_CONTENT_TYPES = {
    BodyType.JSON: 'application/json',
    BodyType.FORM_ENCODED: 'application/x-www-form-urlencoded',
}


def _validate_arg_name(arg, arg_type, reserved):
    # type: (str, str, Set[str]) -> str
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


NO_DEFAULT = object()


class Arg(object):
    """
    Querystring argument
    """

    def __init__(self, name, required=False, default=NO_DEFAULT):
        # type: (str, bool, Union[object, Callable]) -> None
        self.name = name
        self.required = required
        if required and default != NO_DEFAULT:
            raise ValueError(
                'If arg is `required=True` then `default` value is redundant, '
                'as caller must always supply value. If you give a `default` '
                'then `required=True` is not needed as arg will always be sent '
                'with a value.'
            )
        self.default = default


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
                    Arg('type', required=True),
                    Arg('offset_id'),
                    Arg('limit', default=25),
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

    RESERVED_NAMES = ('_request_kwargs', '_session')

    method = None  # type: str
    path = None  # type: str

    body_type = None  # type: str
    body_arg = None  # type: str

    request_headers = None  # type: Optional[Dict[str, str]]

    required_args = None  # type: Set[str]
    url_args = None  # type: Set[str]
    querystring_args = None  # type: Set[Arg]
    request_header_args = None  # type: Dict[str, Set[str]]

    def __init__(self,
                 method,  # type: str
                 path,  # type: str
                 querystring_args=None,  # type: Optional[Tuple[Arg, ...]]
                 request_headers=None,  # type: Optional[Dict[str, str]]
                 body_type=BodyType.JSON,  # type: BodyType
                 body_arg='body',  # type: str
                 body_required=False,  # type: bool
                 ):
        # type: (...) -> None
        """
        Kwargs:
            method: 'GET', 'POST' etc
            path: path portion of url (appended to `APIClient.base_url`)
            querystring_args:
                if given, tuple of non-required arg names, or (<arg name>, True)
                for required args
            request_headers: if given, a dict of
                request headers which will be applied to all requests
            body_type: which kwarg in `requests` lib to use for request
                body, e.g. "data" for form-encoded or "json" for JSON encoded
                (in both cases just pass a python dict in the call)
            body_arg: `body_arg` will be made available as a kwarg in the
                resulting client method, as such it needs a unique name. If the
                default name, "body", is needed as a querystring arg then
                specify a custom arg name here.
            body_required: if request must include a body (e.g. POST) then a
                `MissingRequiredArg` error will be raised if called without it.
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
                all_args.add(
                    _validate_arg_name(arg.name, 'Querystring', reserved)
                )
                if arg.required:
                    required_args.add(arg.name)
                querystring_args_.add(arg)

        # parse request-header args
        request_header_args = {}  # type: Dict[str, Set[str]]
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

        self.body_type = body_type.value
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
