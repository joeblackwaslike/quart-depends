import json
import typing as t

import pytest
from pydantic import BaseModel
from quart import Quart
from quart import Request as QuartRequest

from quart_depends.binders import App
from quart_depends.binders import FromBody
from quart_depends.binders import FromCookie
from quart_depends.binders import FromHeader
from quart_depends.binders import FromJson
from quart_depends.binders import FromPath
from quart_depends.binders import FromQueryData
from quart_depends.binders import FromQueryField
from quart_depends.binders import FromRawJson
from quart_depends.binders import Global
from quart_depends.binders import Request
from quart_depends.extension import QuartDepends


class ReqPayload(BaseModel):
    name: str = ""
    age: int = 0


class CommonQuery(BaseModel):
    q: t.Optional[str] = None
    skip: int = 0
    limit: int = 100


class TestCustomFields:
    path = "/use/nectar"
    content_type = "application/json"
    headers = {"accept": content_type}
    search_string = "test"
    query_params = {"q": search_string}
    payload = dict(name="joejoe", age=12)

    cookie_attrs = dict(server_name="localhost", key="cookie", value="cookie_value")

    @pytest.fixture
    def app(self):
        app = Quart(__name__)
        app.config["QUART_DEPENDS_AUTO_WIRE"] = True
        return app

    @pytest.fixture
    def ext(self):
        return QuartDepends()

    @pytest.fixture
    def test_client(self, app):
        return app.test_client()

    @pytest.mark.parametrize("annotation", [Request, App, Global])
    async def test_quart_framework_deps(self, annotation, app, ext, test_client):
        uri = "/framework-dep"

        @app.route(uri, methods=["GET"])
        async def view(dep: annotation):
            return dict(type=type(dep).__name__)

        ext.init_app(app)

        resp = await test_client.get(uri)

        assert resp.status_code == 200

        result = await resp.get_json()

        origin = annotation.__origin__

        assert result == dict(type=origin.__name__)

    async def test_kitchen_sink(self, app, ext, test_client):
        @app.route("/use/<string:label>", methods=["POST"])
        async def view(
            accept: FromHeader[str] = None,
            request: Request = None,
            q: FromQueryField[str] = None,
            common: FromQueryData[CommonQuery] = None,
            label: FromPath[str] = None,
            payload: FromJson[ReqPayload] = None,
            jsondict: FromRawJson = None,
            body: FromBody[str] = None,
            cookie: FromCookie[str] = None,
        ):
            assert isinstance(request, QuartRequest)
            assert payload.dict() == jsondict

            return dict(
                body=body,
                accept=accept,
                q=str(q),
                label=label,
                payload=payload.dict(),
                common=common.dict(),
                cookie=cookie,
            )

        ext.init_app(app)

        test_client.set_cookie(**self.cookie_attrs)

        resp = await test_client.post(
            self.path,
            headers=self.headers,
            query_string=self.query_params,
            json=self.payload,
        )

        assert resp.status_code == 200
        result = await resp.get_json()

        assert result == dict(
            body=json.dumps(self.payload),
            accept=self.content_type,
            q=self.search_string,
            label=self.path.split("/")[-1],
            payload=self.payload,
            common=CommonQuery(**self.query_params).dict(),
            cookie=self.cookie_attrs["value"],
        )

    async def test_sequenced_payload(self, app, ext, test_client):
        uri = "/sequenced-dep"

        @app.route(uri, methods=["POST"])
        async def view(payload: FromJson[list[ReqPayload]] = None):
            return dict(payload=[p.dict() for p in payload])

        ext.init_app(app)

        request_payload = [self.payload, self.payload, self.payload]
        resp = await test_client.post(uri, json=request_payload)

        assert resp.status_code == 200
        result = await resp.get_json()

        assert result == dict(payload=request_payload)

    async def test_query_binders(self, app, ext, test_client):
        uri = "/query-test"

        @app.route(uri, methods=["GET"])
        async def view(
            paging: FromQueryData[CommonQuery] = None,
            sort: FromQueryField[t.Literal["asc", "desc"]] = None,
        ):
            return dict(paging=paging.dict(), sort=sort)

        ext.init_app(app)

        request_params = self.query_params | dict(sort="asc", q="query")
        resp = await test_client.get(uri, query_string=request_params)

        assert resp.status_code == 200
        result = await resp.get_json()

        assert result == dict(paging=dict(q="query", skip=0, limit=100), sort="asc")

    # async def test_optional_not_required(self, app, ext, test_client):
    #     uri = "/opt-not-required"

    #     @app.route(uri, methods=["POST"])
    #     async def view(
    #         cookie: FromCookie[t.Optional[str]] = None,
    #         # cookie: t.Optional[str] = CookieParam(required=False),
    #     ):
    #         return dict(cookie=cookie)

    #     ext.init_app(app)

    #     resp = await test_client.post(uri)

    #     assert resp.status_code == 200
    #     result = await resp.get_json()

    #     assert result == dict(cookie=None)

    #     test_client.set_cookie(**self.cookie_attrs)
    #     resp = await test_client.post(uri)

    #     assert resp.status_code == 200
    #     result = await resp.get_json()

    #     assert result == dict(cookie=self.cookie_attrs["value"])
