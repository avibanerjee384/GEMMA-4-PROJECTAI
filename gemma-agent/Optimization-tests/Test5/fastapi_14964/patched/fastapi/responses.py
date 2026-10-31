from typing import Any

import warnings

from starlette.responses import FileResponse as FileResponse  # noqa
from starlette.responses import HTMLResponse as HTMLResponse  # noqa
from starlette.responses import JSONResponse as JSONResponse  # noqa
from starlette.responses import PlainTextResponse as PlainTextResponse  # noqa
from starlette.responses import RedirectResponse as RedirectResponse  # noqa
from starlette.responses import Response as Response  # noqa
from starlette.responses import StreamingResponse as StreamingResponse  # noqa

from fastapi.exceptions import FastAPIDeprecationWarning

try:
    import ujson
except ImportError:  # pragma: nocover
    ujson = None  # type: ignore


try:
    import orjson
except ImportError:  # pragma: nocover
    orjson = None  # type: ignore


class UJSONResponse(JSONResponse):
    """
    JSON response using the high-performance ujson library to serialize data to JSON.

    Read more about it in the
    [FastAPI docs for Custom Response - HTML, Stream, File, others](https://fastapi.tiangolo.com/advanced/custom-response/).
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        warnings.warn(
            "UJSONResponse is deprecated. Use JSONResponse instead.",
            category=FastAPIDeprecationWarning,
            stacklevel=2,
        )
        super().__init__(*args, **kwargs)

    def render(self, content: Any) -> bytes:
        assert ujson is not None, "ujson must be installed to use UJSONResponse"
        return ujson.dumps(content, ensure_ascii=False).encode("utf-8")


class ORJSONResponse(JSONResponse):
    """
    JSON response using the high-performance orjson library to serialize data to JSON.

    Read more about it in the
    [FastAPI docs for Custom Response - HTML, Stream, File, others](https://fastapi.tiangolo.com/advanced/custom-response/).
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        warnings.warn(
            "ORJSONResponse is deprecated. Use JSONResponse instead.",
            category=FastAPIDeprecationWarning,
            stacklevel=2,
        )
        super().__init__(*args, **kwargs)

    def render(self, content: Any) -> bytes:
        assert orjson is not None, "orjson must be installed to use ORJSONResponse"
        return orjson.dumps(
            content, option=orjson.OPT_NON_STR_KEYS | orjson.OPT_SERIALIZE_NUMPY
        )
