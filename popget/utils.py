import collections


def update_nested(d, u):
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
        if isinstance(v, collections.Mapping):
            r = update_nested(d.get(k, {}), v)
            d[k] = r
        else:
            d[k] = u[k]
    return d
