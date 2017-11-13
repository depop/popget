from six.moves.urllib import parse as urlparse

from flexisettings.utils import override_settings
import pytest
import requests
import responses

from popget.conf import settings
from popget.client import (
    APIEndpoint,
    APIClient,
    ArgNameConflict,
    MissingRequiredArg,
    FORM_ENCODED,
)


def test_method_and_path():
    endpoint = APIEndpoint('GET', '/dummy/')
    assert endpoint.method == 'get'
    assert endpoint.path == '/dummy/'

    endpoint = APIEndpoint('POST', '/dummy/{user_id}/')
    assert endpoint.method == 'post'
    assert endpoint.path == '/dummy/{user_id}/'


def test_body_arg_ok():
    """
    Can customise the arg name used for the request body in method kwargs.
    """
    endpoint = APIEndpoint(
        'POST',
        '/dummy/',
        body_arg='_body',
    )
    assert endpoint.body_arg == '_body'
    assert '_body' not in endpoint.required_args


def test_body_arg_required():
    """
    Can mark the arg name used for the request body as required.
    """
    endpoint = APIEndpoint(
        'POST',
        '/dummy/',
        body_arg='_body',
        body_required=True,
    )
    assert endpoint.body_arg == '_body'
    assert '_body' in endpoint.required_args


def test_body_arg_clash():
    """
    Cannot use a reserved name for the request body arg.
    """
    with pytest.raises(ArgNameConflict):
        APIEndpoint(
            'POST',
            '/dummy/',
            body_arg='_request_kwargs',  # reserved name
        )


def test_url_args_ok():
    """
    Url args are parsed out of the endpoint path format string. Url args are
    always required. They are added to the other required args.
    """
    endpoint = APIEndpoint(
        'GET',
        '/chat/{thread_id}/messages/{message_id}/',
        body_required=True,
    )
    assert endpoint.url_args == {'thread_id', 'message_id'}
    assert endpoint.required_args == {'thread_id', 'message_id', 'body'}


def test_url_args_clash():
    """
    Cannot use any reserved or already used names for url args.
    """
    # body_arg clash
    with pytest.raises(ArgNameConflict):
        APIEndpoint(
            'GET',
            '/bodies/{body}/',
        )

    # reserved name clash
    with pytest.raises(ArgNameConflict):
        APIEndpoint(
            'GET',
            '/bodies/{_request_kwargs}/',
        )


def test_querystring_args_ok():
    """
    Querystring args are supported in both tuple and string form.
    When specified via a tuple it is possible to mark the arg as required.
    """
    endpoint = APIEndpoint(
        'GET',
        '/users/{user_id}/feedback/',
        querystring_args=(
            ('role', True),  # required
            ('offset', False),  # optional
            'limit',  # optional
        ),
    )
    assert endpoint.url_args == {'user_id'}
    assert endpoint.querystring_args == {'role', 'offset', 'limit'}
    assert endpoint.required_args == {'user_id', 'role'}


def test_querystring_args_clash():
    """
    Cannot use any reserved or already used names for querystring args.
    """
    # body_arg clash
    with pytest.raises(ArgNameConflict):
        APIEndpoint(
            'GET',
            '/users/{user_id}/feedback/',
            querystring_args=('body',),
        )

    # reserved name clash
    with pytest.raises(ArgNameConflict):
        APIEndpoint(
            'GET',
            '/users/{user_id}/feedback/',
            querystring_args=('_request_kwargs',),
        )

    # if same arg name appears in url and querystring it's assumed you
    # want to use the same value for both
    endpoint = APIEndpoint(
        'GET',
        '/users/{user_id}/feedback/',
        querystring_args=('user_id',),
    )
    assert endpoint.url_args == {'user_id'}
    assert endpoint.querystring_args == {'user_id'}


def test_request_header_args_ok():
    """
    Url args are parsed out of the format string for each header value.
    Request-header args are always required.
    """
    endpoint = APIEndpoint(
        'GET',
        '/users/{user_id}/items/',
        request_headers={
            'Authorization': 'Bearer {token}',
            'X-Depop-Edition': '{edition}'
        },
    )
    assert endpoint.request_header_args == {
        'Authorization': {'token'},
        'X-Depop-Edition': {'edition'},
    }
    assert endpoint.required_args == {'user_id', 'token', 'edition'}


def test_request_header_args_clash():
    """
    Cannot use any reserved or already used names for request-header args.
    """
    # body_arg clash
    with pytest.raises(ArgNameConflict):
        APIEndpoint(
            'GET',
            '/sandwiches/',
            request_headers={
                'X-Depop-WTF': '{body}',
            },
        )

    # reserved name clash
    with pytest.raises(ArgNameConflict):
        APIEndpoint(
            'GET',
            '/whatever/',
            request_headers={
                'Authorization': '{_request_kwargs}',
            },
        )

    # if same arg name appears in request-headers and url args
    # it's assumed you want to use the same value for both
    endpoint = APIEndpoint(
        'GET',
        '/users/{user_id}/feedback/',
        request_headers={
            'Authorization': '{user_id}',
        },
    )
    assert endpoint.url_args == {'user_id'}
    assert endpoint.request_header_args == {
        'Authorization': {'user_id'},
    }
    # if same arg name appears in request-headers and querystring args
    # it's assumed you want to use the same value for both
    endpoint = APIEndpoint(
        'GET',
        '/users/feedback/',
        querystring_args=('role',),
        request_headers={
            'X-Depop-Role': '{role}',
        },
    )
    assert endpoint.querystring_args == {'role'}
    assert endpoint.request_header_args == {
        'X-Depop-Role': {'role'},
    }


class DummyService(APIClient):

    base_url = 'http://baseurl.com/'

    thing_detail = APIEndpoint(
        'GET',
        '/v1/thing/{id}',
    )
    thing_update = APIEndpoint(
        'PATCH',
        '/v1/thing/{id}',
        body_type=FORM_ENCODED,
    )
    thing_create = APIEndpoint(
        'POST',
        '/v1/thing/',
        request_headers={
            'Authorization': 'Bearer {token}'
        }
    )
    thing_list = APIEndpoint(
        'GET',
        '/v1/thing/',
        querystring_args=(
            ('type', True),  # required
            'whatever',  # optional
        ),
    )
    thing_delete = APIEndpoint(
        'DELETE',
        '/v1/thing/{thing_id}',
        request_headers={
            'X-Depop-Thing': '{thing_id}'
        }
    )


@responses.activate
def test_raise_for_status():
    """
    Test that we raise a `requests.HTTPError` for 40x/50x response status
    """
    responses.add(responses.GET, 'http://baseurl.com/v1/thing/777',
                  body='{"error": "Not found."}', status=404,
                  content_type='application/json')

    with pytest.raises(requests.exceptions.HTTPError):
        DummyService.thing_detail(id=777)


@responses.activate
def test_get_detail():
    """
    Get request with url arg. Response with json content-type is deserialized.
    """
    responses.add(responses.GET, 'http://baseurl.com/v1/thing/777',
                  body='{"thing": "it\'s a thing"}', status=200,
                  content_type='application/json')

    data = DummyService.thing_detail(id=777)
    assert data == {"thing": "it's a thing"}


@responses.activate
def test_non_json_response():
    """
    If response does not have a json content-type then don't try to deserialize it.
    """
    responses.add(responses.GET, 'http://baseurl.com/v1/thing/777',
                  body="It's your thing, do what you want to do.", status=200,
                  content_type='text/html')

    data = DummyService.thing_detail(id=777)
    assert data == "It's your thing, do what you want to do."


@responses.activate
def test_get_missing_url_arg():
    """
    Url args are required, missing arg raises an exception
    """
    responses.add(responses.GET, 'http://baseurl.com/v1/thing/777',
                  body='{"thing": "it\'s a thing"}', status=200,
                  content_type='application/json')

    with pytest.raises(MissingRequiredArg):
        DummyService.thing_detail()


@responses.activate
def test_get_with_querystring():
    """
    Get request with querystring args.
    """
    def callback(request):
        query = urlparse.parse_qs(urlparse.urlparse(request.url).query)
        # expected querystring args were passed:
        assert query == {
                'type': ['chair'],
                'whatever': ['upholstery'],
            }
        return (200, {}, '[{"thing": "Chippendale"}]')

    responses.add_callback(responses.GET, 'http://baseurl.com/v1/thing/',
                           callback=callback,
                           content_type='application/json')

    DummyService.thing_list(type='chair', whatever='upholstery')


@responses.activate
def test_get_missing_querystring_arg():
    """
    Request with querystring args. Missing arg required raises an exception,
    missing optional arg is ignored.
    """
    responses.add(responses.GET, 'http://baseurl.com/v1/thing/',
                  body='[{"thing": "Chippendale"}]', status=200,
                  content_type='application/json')

    # missing required arg
    with pytest.raises(MissingRequiredArg):
        DummyService.thing_list(whatever='upholstery')

    # missing optional arg
    DummyService.thing_list(type='chair')


@responses.activate
def test_post_json():
    """
    Post request with a JSON post body and a request-header arg.
    """
    def callback(request):
        # expected post body was passed:
        assert request.body == b'{"thing": "it\'s my thing"}'
        # expected header was present:
        assert 'Authorization' in request.headers
        assert request.headers['Authorization'] == 'Bearer of gratitude'
        return (200, {}, 'Do what you want to do.')

    responses.add_callback(responses.POST, 'http://baseurl.com/v1/thing/',
                           callback=callback,
                           content_type='text/plain')

    DummyService.thing_create(
        body={"thing": "it's my thing"},
        token='of gratitude'
    )


@responses.activate
def test_patch_form_encoded():
    """
    Patch request with a form-encoded post body and a url arg.
    """
    def callback(request):
        # expected post body was passed:
        assert 'description=a+whole+other+thing' in request.body
        assert 'type=coffee+table' in request.body
        return (200, {}, 'OK')

    responses.add_callback(responses.PATCH, 'http://baseurl.com/v1/thing/777',
                           callback=callback,
                           content_type='text/plain')

    DummyService.thing_update(
        id=777,
        body={
            "description": "a whole other thing",
            "type": "coffee table",
        },
    )


@responses.activate
def test_delete_arg_sharing():
    """
    Delete request with same arg name repeated in url and request headers.
    Value from the kwarg is used for both.
    """
    def callback(request):
        # expected header was present:
        assert 'X-Depop-Thing' in request.headers
        assert request.headers['X-Depop-Thing'] == '777'
        return (200, {}, 'OK')

    responses.add_callback(responses.DELETE, 'http://baseurl.com/v1/thing/777',
                           callback=callback,
                           content_type='text/plain')

    DummyService.thing_delete(thing_id=777)


@override_settings(settings, CLIENT_TIMEOUT=0.0001)
def test_timeout():
    """
    Test APIClient behaviour when the requests library timeout threshold is reached
    """
    with pytest.raises(requests.exceptions.HTTPError) as e:
        DummyService.thing_detail(id=777)
        assert e.response.status_code == 504
