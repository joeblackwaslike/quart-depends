import typing as t

from quart import Quart, Request, request

from quart_depends import Depends, QuartDepends

app = Quart(__name__)
app.config["QUART_DEPENDS_AUTO_WIRE"] = True
depends = QuartDepends()


def get_request():
    return request._get_current_object()


QuartRequest = t.Annotated[Request, Depends(get_request, cast=False)]


@app.route("/")
def endpoint(request: QuartRequest = None):
    return dict(
        headers=dict(request.headers),
    )


depends.init_app(app)


async def test_provider():
    test_client = app.test_client()

    resp = await test_client.get(
        "/", headers={"accept": "application/json", "secret_api_key": "df23dg3d52wri9"}
    )
    result = await resp.get_json()

    assert result["headers"]["Secret_Api_Key"] == "df23dg3d52wri9"

    def get_fake_request():
        req = request._get_current_object()
        req.headers["Secret_Api_Key"] = "fake value"
        return req

    depends.provider.override(get_request, get_fake_request)

    test_client = app.test_client()
    resp = await test_client.get("/", headers={})
    result = await resp.get_json()

    assert result["headers"]["Secret_Api_Key"] == "fake value"
