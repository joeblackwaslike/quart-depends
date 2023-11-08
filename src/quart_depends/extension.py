import logging
from functools import wraps

from fast_depends import Depends, inject
from fast_depends.dependencies.provider import Provider
from quart import Quart

from quart_depends.wiring import wire_app

logger = logging.getLogger(__name__)


def wrap_inject(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return inject(func)(*args, **kwargs)

    return wrapper


def wrap_Depends(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper


Depends = wrap_Depends(Depends)


class QuartDepends:
    def __init__(self):
        self.provider = Provider()

    def init_app(self, app: Quart):
        auto_wire_app = app.config.get("QUART_DEPENDS_AUTO_WIRE", False)
        if auto_wire_app:
            logger.info("Auto wiring app with @inject")
            wire_app(app, self.provider)
        else:
            logger.warn(
                "Auto wiring disabled.  Remember to manually apply @inject to your views using Depends"
            )

        app.extensions["quart_depends"] = self
