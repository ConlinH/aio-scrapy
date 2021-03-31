# _*_ coding: utf-8 _*_

import asyncio


async def call_helper(f, *args, **kwargs):
    if asyncio.iscoroutinefunction(f):
        return await f(*args, **kwargs)
    return f(*args, **kwargs)


async def iter_errback(iterable, errback, *a, **kw):
    """Wraps an iterable calling an errback if an error is caught while
    iterating it.
    """
    it = iter(iterable)
    while True:
        try:
            yield next(it)
        except StopIteration:
            break
        except Exception as exc:
            await errback(exc, *a, **kw)


def get_project_settings():
    import os
    import pickle
    import warnings

    from scrapy.utils.conf import init_env
    from aioscrapy.settings import AioSettings
    from scrapy.exceptions import ScrapyDeprecationWarning

    ENVVAR = 'SCRAPY_SETTINGS_MODULE'

    if ENVVAR not in os.environ:
        project = os.environ.get('SCRAPY_PROJECT', 'default')
        init_env(project)
    settings = AioSettings()
    settings_module_path = os.environ.get(ENVVAR)
    if settings_module_path:
        settings.setmodule(settings_module_path, priority='project')

    pickled_settings = os.environ.get("SCRAPY_PICKLED_SETTINGS_TO_OVERRIDE")
    if pickled_settings:
        warnings.warn("Use of environment variable "
                      "'SCRAPY_PICKLED_SETTINGS_TO_OVERRIDE' "
                      "is deprecated.", ScrapyDeprecationWarning)
        settings.setdict(pickle.loads(pickled_settings), priority='project')

    scrapy_envvars = {k[7:]: v for k, v in os.environ.items() if
                      k.startswith('SCRAPY_')}
    valid_envvars = {
        'CHECK',
        'PICKLED_SETTINGS_TO_OVERRIDE',
        'PROJECT',
        'PYTHON_SHELL',
        'SETTINGS_MODULE',
    }
    setting_envvars = {k for k in scrapy_envvars if k not in valid_envvars}
    if setting_envvars:
        setting_envvar_list = ', '.join(sorted(setting_envvars))
        warnings.warn(
            'Use of environment variables prefixed with SCRAPY_ to override '
            'settings is deprecated. The following environment variables are '
            f'currently defined: {setting_envvar_list}',
            ScrapyDeprecationWarning
        )
    settings.setdict(scrapy_envvars, priority='project')

    return settings


def singleton(cls):
    _instance = {}

    def _singleton(*args, **kwargs):
        if cls not in _instance:
            _instance[cls] = cls(*args, **kwargs)
        return _instance[cls]

    return _singleton


def exec_js_func(js_file, func, *params):
    import execjs
    with open(js_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    js = ''.join(lines)
    js_context = execjs.compile(js)
    return js_context.call(func, *params)
