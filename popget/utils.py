import collections
from types import MappingProxyType
from typing import Any


def update_nested(d: dict, u: collections.abc.Mapping) -> dict:
    """
    https://stackoverflow.com/a/3233356/202168
    A dict update that supports nested keys without overwriting the whole
    sub-dict like the built-in `update` method of dicts.

    e.g.

    mydict = {
        'a': {
            'b': 1
        }
    }
    mydict.update({'a': {'c': 2}})

    assert mydict == {
        'a': {
            'b': 1,
            'c': 2,
        }
    }
    """
    for k, v in u.items():
        if isinstance(v, collections.abc.Mapping):
            r = update_nested(d.get(k, {}), v)
            d[k] = r
        else:
            d[k] = u[k]
    return d


def get_base_attr(attr: str, bases: tuple[type, ...], attrs: dict[str, Any] | MappingProxyType) -> object | None:
    """
    Given an attr name, recursively look through the given base classes
    until finding one where that attr is present, returning the value.
    """
    try:
        return attrs[attr]
    except KeyError:
        pass
    for base in bases:
        try:
            return get_base_attr(attr, base.__bases__, base.__dict__)
        except KeyError:
            pass
    return None


class classproperty(property):
    def __get__(self, cls, owner):
        return classmethod(self.fget).__get__(None, owner)()
