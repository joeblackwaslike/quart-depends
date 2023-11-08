import typing as t

import quart
from fast_depends import Depends
from fast_depends.library import CustomField
from quart import Quart
from quart import Request as QuartRequest
from quart import Websocket as QuartWebsocket
from quart.ctx import _AppCtxGlobals as AppCtxGlobals
from quart.sessions import SessionMixin as QuartSession

T = t.TypeVar("T")


def get_quart_request() -> QuartRequest:
    return quart.request._get_current_object()


def get_quart_app() -> quart.Quart:
    return quart.current_app._get_current_object()


def get_quart_g() -> quart.ctx._AppCtxGlobals:
    return quart.g._get_current_object()


def get_quart_websocket() -> quart.Websocket:
    return quart.websocket._get_current_object()


def get_quart_session() -> QuartSession:
    return quart.session._get_current_object()


def transform_underscores_to_hyphens(text: str):
    return text.replace("_", "-")


class HeaderParam(CustomField):
    def __init__(self, convert_underscores=True, **kwargs) -> None:
        self.convert_underscores = convert_underscores
        super().__init__(**kwargs)

    def use(self, **kwargs):
        request = get_quart_request()

        param_name = (
            transform_underscores_to_hyphens(self.param_name)
            if self.convert_underscores
            else self.param_name
        )
        return {**super().use(**kwargs), self.param_name: request.headers[param_name]}


class CookieParam(CustomField):
    def __init__(self, convert_underscores=True, **kwargs) -> None:
        self.convert_underscores = convert_underscores
        super().__init__(**kwargs)

    def use(self, **kwargs):
        request = get_quart_request()

        param_name = (
            transform_underscores_to_hyphens(self.param_name)
            if self.convert_underscores
            else self.param_name
        )
        return {**super().use(**kwargs), self.param_name: request.cookies[param_name]}


class PathParam(CustomField):
    def use(self, **kwargs):
        request = get_quart_request()
        return {**super().use(**kwargs), self.param_name: request.view_args[self.param_name]}


class QueryData(CustomField):
    def use(self, **kwargs):
        request = get_quart_request()
        return {**super().use(**kwargs), self.param_name: dict(request.args)}


class QueryParam(CustomField):
    def use(self, **kwargs):
        request = get_quart_request()
        if self.required and self.param_name not in request.args:
            raise ValueError(f"Missing required query parameter: {self.param_name}")
        return {**super().use(**kwargs), self.param_name: request.args[self.param_name]}


class Body(CustomField):
    async def use(self, **kwargs):
        request = get_quart_request()
        payload = await request.get_data()
        return {**super().use(**kwargs), self.param_name: payload}


class JsonBody(CustomField):
    async def use(self, **kwargs):
        request = get_quart_request()
        payload = await request.get_json()
        return {**super().use(**kwargs), self.param_name: payload}


Request = t.Annotated[QuartRequest, Depends(get_quart_request)]
App = t.Annotated[Quart, Depends(get_quart_app)]
Global = t.Annotated[AppCtxGlobals, Depends(get_quart_g)]
Websocket = t.Annotated[QuartWebsocket, Depends(get_quart_websocket)]
Session = t.Annotated[QuartSession, Depends(get_quart_session)]

FromHeader = t.Annotated[T, HeaderParam()]
FromQueryData = t.Annotated[T, QueryData()]
FromQueryField = t.Annotated[T, QueryParam()]
FromPath = t.Annotated[T, PathParam()]
FromCookie = t.Annotated[T, CookieParam()]
FromJson = t.Annotated[T, JsonBody()]
FromBody = t.Annotated[T, Body()]
FromRawJson = t.Annotated[dict, JsonBody()]
