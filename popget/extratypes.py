from typing import Any, Dict, List, Union


_T = Any  # should be 'JSONTypes' but mypy doesn't support recursive types yet

JSONTypes = Union[Dict[str, _T], List[_T], str, float, bool, None]

JSONObject = Dict[str, JSONTypes]

JSONList = List[JSONTypes]

ResponseTypes = Union[bytes, JSONTypes]
