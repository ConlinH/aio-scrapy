import warnings
from functools import wraps

from aioscrapy.exceptions import AioScrapyDeprecationWarning


def deprecated(use_instead=None):
    """This is a decorator which can be used to mark functions
    as deprecated. It will result in a warning being emitted
    when the function is used."""

    def deco(func):
        @wraps(func)
        def wrapped(*args, **kwargs):
            message = f"Call to deprecated function {func.__name__}."
            if use_instead:
                message += f" Use {use_instead} instead."
            warnings.warn(message, category=AioScrapyDeprecationWarning, stacklevel=2)
            return func(*args, **kwargs)
        return wrapped

    if callable(use_instead):
        deco = deco(use_instead)
        use_instead = None
    return deco
