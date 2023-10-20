import typing as t

from quart import Quart, jsonify


def create_app(
    blueprint: t.Optional[t.Any] = None,
    extension: t.Optional[t.Any] = None,
    config=None,
):
    config = config or {}
    config.setdefault("ENV", "development")
    config.setdefault("PRESERVE_CONTEXT_ON_EXCEPTION", True)

    app = Quart(__name__)
    app.config.from_mapping(config)
    if blueprint:
        app.register_blueprint(blueprint)
    if extension:
        extension.init_app(app)

    register_json_error_handlers(app)

    return app


def register_json_error_handlers(app: Quart):
    @app.errorhandler(401)
    def handle_401(e):
        return jsonify(error=str(e)), 401

    @app.errorhandler(403)
    def handle_403(e):
        return jsonify(error=str(e)), 403

    @app.errorhandler(404)
    def handle_404(e):
        return jsonify(error=str(e)), 404

    @app.errorhandler(405)
    def handle_405(e):
        return jsonify(error=str(e)), 405

    @app.errorhandler(422)
    def handle_422(e):
        return jsonify(error=str(e)), 422

    @app.errorhandler(500)
    def handle_500(e):
        return jsonify(error=str(e)), 500
