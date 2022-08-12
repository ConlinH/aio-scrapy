"""Helper functions which don't fit anywhere else"""

from importlib import import_module
from pkgutil import iter_modules

from aioscrapy.utils.tools import call_helper


def walk_modules(path):
    """Loads a module and all its submodules from the given module path and
    returns them. If *any* module throws an exception while importing, that
    exception is thrown back.

    For example: walk_modules('aioscrapy.utils')
    """

    mods = []
    mod = import_module(path)
    mods.append(mod)
    if hasattr(mod, '__path__'):
        for _, subpath, ispkg in iter_modules(mod.__path__):
            fullpath = path + '.' + subpath
            if ispkg:
                mods += walk_modules(fullpath)
            else:
                submod = import_module(fullpath)
                mods.append(submod)
    return mods


def load_object(path: str):
    """Load an object given its absolute object path, and return it.

    The object can be the import path of a class, function, variable or an
    instance, e.g. 'aioscrapy.libs.downloader.redirect.RedirectMiddleware'..
    """
    try:
        dot = path.rindex('.')
    except ValueError:
        raise ValueError(f"Error loading object '{path}': not a full path")

    module, name = path[:dot], path[dot + 1:]
    mod = import_module(module)

    try:
        obj = getattr(mod, name)
    except AttributeError:
        raise NameError(f"Module '{module}' doesn't define any object named '{name}'")

    return obj


async def create_instance(objcls, settings, crawler, *args, spider=None, **kwargs):
    """Construct a class instance using its ``from_crawler`` or
    ``from_settings`` constructors, if available.

    At least one of ``settings`` and ``crawler`` needs to be different from
    ``None``. If ``settings `` is ``None``, ``crawler.settings`` will be used.
    If ``crawler`` is ``None``, only the ``from_settings`` constructor will be
    tried.

    ``*args`` and ``**kwargs`` are forwarded to the constructors.

    Raises ``ValueError`` if both ``settings`` and ``crawler`` are ``None``.

    .. versionchanged:: 2.2
       Raises ``TypeError`` if the resulting instance is ``None`` (e.g. if an
       extension has not been implemented correctly).
    """
    if settings is None:
        if crawler is None and spider is None:
            raise ValueError("Specify at least one of settings, crawler and spider.")

        settings = crawler and crawler.settings or spider and spider.settings
        spider = spider or crawler and crawler.spider

    if crawler and hasattr(objcls, 'from_crawler'):
        instance = await call_helper(objcls.from_crawler, crawler, *args, **kwargs)
        method_name = 'from_crawler'
    elif spider and hasattr(objcls, 'from_spider'):
        instance = await call_helper(objcls.from_spider, spider, *args, **kwargs)
        method_name = 'from_spider'
    elif hasattr(objcls, 'from_settings'):
        instance = await call_helper(objcls.from_settings, settings, *args, **kwargs)
        method_name = 'from_settings'
    else:
        instance = objcls(*args, **kwargs)
        method_name = '__new__'
    if instance is None:
        raise TypeError(f"{objcls.__qualname__}.{method_name} returned None")
    return instance


async def load_instance(clspath: str, *args, settings=None, spider=None, crawler=None, **kwargs):
    return await create_instance(
        load_object(clspath),
        settings,
        crawler,
        *args,
        spider=spider,
        **kwargs
    )
