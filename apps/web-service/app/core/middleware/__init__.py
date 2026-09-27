import inspect

from fastapi import FastAPI

from app.core.middleware import cors, response, process_time

MIDDLEWARES = [cors.MIDDLEWARE, response.MIDDLEWARE, process_time.MIDDLEWARE]


def register_middleware(app: FastAPI) -> None:
    for callable_obj, kwargs in MIDDLEWARES:
        if inspect.isclass(callable_obj):
            app.add_middleware(callable_obj, **kwargs)  # type: ignore
        else:
            app.middleware("http")(callable_obj)
