
import os
import shutil
import sys
import tempfile
from contextlib import contextmanager

import pkg_resources

try:
    from scrapyd import get_application
    from scrapyd.interfaces import IEggStorage
except ImportError:
    pass


def activate_egg(eggpath):
    """Activate a Scrapy egg file. This is meant to be used from egg runners
    to activate a Scrapy egg file. Don't use it from other code as it may
    leave unwanted side effects.
    """
    try:
        d = next(pkg_resources.find_distributions(eggpath))
    except StopIteration:
        raise ValueError("Unknown or corrupt egg")
    d.activate()
    settings_module = d.get_entry_info('aioscrapy', 'settings').module_name
    os.environ.setdefault('AIOSCRAPY_SETTINGS_MODULE', settings_module)


@contextmanager
def project_environment(project):
    app = get_application()
    eggstorage = app.getComponent(IEggStorage)
    eggversion = os.environ.get('AIOSCRAPY_EGG_VERSION', None)
    version, eggfile = eggstorage.get(project, eggversion)
    if eggfile:
        prefix = '%s-%s-' % (project, version)
        fd, eggpath = tempfile.mkstemp(prefix=prefix, suffix='.egg')
        lf = os.fdopen(fd, 'wb')
        shutil.copyfileobj(eggfile, lf)
        lf.close()
        activate_egg(eggpath)
    else:
        eggpath = None
    try:
        assert 'aioscrapy.conf' not in sys.modules, "aioscrapy settings already loaded"
        yield
    finally:
        if eggpath:
            os.remove(eggpath)


def main():
    os.environ.update({f'AIO{k}': v for k, v in os.environ.items() if k.startswith('SCRAPY_')})

    project = os.environ['AIOSCRAPY_PROJECT']
    with project_environment(project):
        from aioscrapy.cmdline import execute
        execute()


if __name__ == '__main__':
    main()
