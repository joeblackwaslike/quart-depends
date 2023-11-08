import functools
import inspect
import typing as t

import quart
import quart.views
from fast_depends import inject
from quart import Quart


def _wrap_view_class(view_func: t.Callable, app: Quart, provider, wrapper) -> t.Callable:
    cls: type[quart.views.View] = t.cast(t.Any, view_func).view_class

    while getattr(view_func, "__wrapped__", None):  # pylint: disable=while-used
        view_func = view_func.__wrapped__

    closure = inspect.getclosurevars(view_func)

    if closure.nonlocals.get("class_args"):
        raise RuntimeError(
            "cannot pass positional args to View.as_view() when using quart-injector"
        )

    class_kwargs = closure.nonlocals["class_kwargs"]

    async def view(*args: t.Any, **kwargs: t.Any) -> t.Any:
        self = cls(**class_kwargs)
        wrapped = wrapper(dependency_overrides_provider=provider)(self.dispatch_request)
        return await app.ensure_async(wrapped)(*args, **kwargs)

    if cls.decorators:
        view.__name__ = cls.__name__
        view.__module__ = cls.__module__
        for decorator in cls.decorators:
            view = decorator(view)

    setattr(view, "view_class", cls)
    view.__name__ = cls.__name__
    view.__doc__ = cls.__doc__
    view.__module__ = cls.__module__
    setattr(view, "methods", cls.methods)
    setattr(view, "provide_automatic_options", cls.provide_automatic_options)
    return view


def wrap(
    view_func: t.Callable,
    app: Quart,
    provider,
    wrapper,
) -> t.Callable:
    if getattr(view_func, "_quart_depends_wrapped", False):
        return view_func

    if hasattr(view_func, "view_class"):
        result = _wrap_view_class(view_func, app, provider, wrapper)
        setattr(result, "_quart_depends_wrapped", True)
        return result

    @functools.wraps(view_func)
    async def view(*args: t.Any, **kwargs: t.Any) -> t.Any:
        wrapped = wrapper(dependency_overrides_provider=provider)(view_func)
        return await app.ensure_async(wrapped)(*args, **kwargs)

    setattr(view, "_quart_depends_wrapped", True)

    return view


def _wire_collection(value: t.Any, app: Quart, provider, wrapper) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if isinstance(item, (list, dict)):
                _wire_collection(item, app, provider, wrapper)
            else:
                value[key] = wrap(item, app, provider, wrapper)

    if isinstance(value, list):
        value[:] = [wrap(item, app, provider, wrapper) for item in value]


def wire_app(app: Quart, provider, wrapper=inject) -> None:
    _wire_collection(app.before_request_funcs, app, provider, wrapper)
    _wire_collection(app.teardown_request_funcs, app, provider, wrapper)
    _wire_collection(app.after_request_funcs, app, provider, wrapper)
    _wire_collection(app.before_websocket_funcs, app, provider, wrapper)
    _wire_collection(app.teardown_websocket_funcs, app, provider, wrapper)
    _wire_collection(app.after_websocket_funcs, app, provider, wrapper)

    _wire_collection(app.before_serving_funcs, app, provider, wrapper)
    _wire_collection(app.teardown_appcontext_funcs, app, provider, wrapper)
    _wire_collection(app.after_serving_funcs, app, provider, wrapper)

    _wire_collection(app.view_functions, app, provider, wrapper)
    _wire_collection(app.error_handler_spec, app, provider, wrapper)
    _wire_collection(app.template_context_processors, app, provider, wrapper)
