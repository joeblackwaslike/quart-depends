import typing as t

from quart import Quart, Request, Response, request

from quart_depends import Depends
from quart_depends.extension import QuartDepends

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


@app.before_request
def handle_before_request(request: QuartRequest = None):
    print(f"before_request: {request}")


@app.teardown_request
def handle_teardown_request(exc: t.Optional[Exception] = None, request: QuartRequest = None):
    print(f"teardown_request: {request}")


@app.after_request
def handle_after_request(
    response: Response,
    request: QuartRequest = None,
):
    print(f"after_request: {request}")
    # after_request handler has to return a response
    return response


@app.context_processor
def add_to_the_context():
    return dict(depends=depends)


depends.init_app(app)


async def test_extension():
    test_client = app.test_client()
    resp = await test_client.get(
        "/",
        headers={
            "accept": "application/json",
            "secret_api_key": "df23dg3d52wri9",
        },
    )
    result = await resp.get_json()

    assert result["headers"]["Secret_Api_Key"] == "df23dg3d52wri9"
