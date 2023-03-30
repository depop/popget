from typing import Any


_T = Any  # should be 'JSONTypes' but mypy doesn't support recursive types yet

JSONTypes = dict[str, _T] | list[_T] | str | float | bool | None

JSONObject = dict[str, JSONTypes]

JSONList = list[JSONTypes]

ResponseTypes = bytes | JSONTypes
