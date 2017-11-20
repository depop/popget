import pytest
import requests
import responses

from popget.async.threadpool import APIClient
from popget.endpoint import APIEndpoint, BodyType


class DummyService(APIClient):

    class Config:
        base_url = 'http://baseurl.com/'

    thing_detail = APIEndpoint(
        'GET',
        '/v1/thing/{id}',
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
def test_async_raise_for_status():
    """
    Test that we raise a `requests.HTTPError` for 40x/50x response status
    """
    responses.add(responses.GET, 'http://baseurl.com/v1/thing/777',
                  body='{"error": "Not found."}', status=404,
                  content_type='application/json')

    future = DummyService.async_thing_detail(id=777)
    with pytest.raises(requests.exceptions.HTTPError):
        future.result()


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
def test_async_get_detail():
    """
    Get request with url arg. Response with json content-type is deserialized.
    """
    responses.add(responses.GET, 'http://baseurl.com/v1/thing/777',
                  body='{"thing": "it\'s a thing"}', status=200,
                  content_type='application/json')

    future = DummyService.async_thing_detail(id=777)
    data = future.result()
    assert data == {"thing": "it's a thing"}


class CustomDummyService(APIClient):

    class Config:
        base_url = 'http://baseurl.com/'
        async_method_template = '{}_async'

    thing_detail = APIEndpoint(
        'GET',
        '/v1/thing/{id}',
    )


@responses.activate
def test_async_get_detail_custom_method_name():
    """
    We can set a custom method name template for async methods.
    """
    responses.add(responses.GET, 'http://baseurl.com/v1/thing/777',
                  body='{"thing": "it\'s a thing"}', status=200,
                  content_type='application/json')

    future = CustomDummyService.thing_detail_async(id=777)
    data = future.result()
    assert data == {"thing": "it's a thing"}
