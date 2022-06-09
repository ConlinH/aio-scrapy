import inspect
import logging

from aioscrapy.spiders import Spider


logger = logging.getLogger(__name__)


def iter_spider_classes(module):
    """Return an iterator over all spider classes defined in the given module
    that can be instantiated (i.e. which have name)
    """
    # this needs to be imported here until get rid of the spider manager
    # singleton in aioscrapy.spider.spiders

    for obj in vars(module).values():
        if (
            inspect.isclass(obj)
            and issubclass(obj, Spider)
            and obj.__module__ == module.__name__
            and getattr(obj, 'name', None)
        ):
            yield obj
