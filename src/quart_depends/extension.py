from fast_depends.dependencies.provider import Provider
from quart import Quart

from quart_depends.wiring import wire_app


class QuartDepends:
    def __init__(self):
        self.provider = Provider()

    def init_app(self, app: Quart):
        wire_app(app, self.provider)
        app.extensions["quart_depends"] = self
