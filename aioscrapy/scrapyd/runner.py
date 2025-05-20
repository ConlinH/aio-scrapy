
"""
Scrapyd Runner Module
Scrapyd运行器模块

This module provides utilities for running AioScrapy spiders from egg files deployed
with Scrapyd. It handles the activation of egg files, setting up the project environment,
and launching the spider.
此模块提供了从使用Scrapyd部署的egg文件运行AioScrapy爬虫的实用程序。它处理egg文件的激活、
设置项目环境和启动爬虫。

The main components are:
主要组件包括：

1. activate_egg: Activates a Scrapy egg file and sets up the environment
                激活Scrapy egg文件并设置环境
2. project_environment: Context manager that sets up the project environment
                       设置项目环境的上下文管理器
3. main: Entry point for running spiders from Scrapyd
        从Scrapyd运行爬虫的入口点

This module is designed to be used by Scrapyd to run AioScrapy spiders, but it can
also be used directly to run spiders from egg files.
此模块设计用于Scrapyd运行AioScrapy爬虫，但也可以直接用于从egg文件运行爬虫。
"""
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
    """
    Activate a Scrapy egg file.
    激活aioscrapy egg文件。

    This function activates a aioscrapy egg file by adding it to the Python path
    and setting the AIOSCRAPY_SETTINGS_MODULE environment variable to the
    settings module specified in the egg's entry points.
    此函数通过将aioscrapy egg文件添加到Python路径并将AIOSCRAPY_SETTINGS_MODULE
    环境变量设置为egg入口点中指定的设置模块来激活它。

    This is meant to be used from egg runners to activate a Scrapy egg file.
    Don't use it from other code as it may leave unwanted side effects.
    这旨在从egg运行器使用，以激活Scrapy egg文件。不要从其他代码中使用它，
    因为它可能会留下不必要的副作用。

    Args:
        eggpath: Path to the egg file to activate.
                要激活的egg文件的路径。

    Raises:
        ValueError: If the egg file is unknown or corrupt.
                   如果egg文件未知或损坏。
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
    """
    Set up the environment for a aioscrapy project.
    为aioscrapy项目设置环境。

    This context manager sets up the environment for a aioscrapy project by:
    此上下文管理器通过以下方式为aioscrapy项目设置环境：

    1. Retrieving the egg file for the project from aioscrapyd's egg storage
       从aioscrapyd的egg存储中检索项目的egg文件
    2. Creating a temporary copy of the egg file
       创建egg文件的临时副本
    3. Activating the egg file
       激活egg文件
    4. Cleaning up the temporary egg file when done
       完成后清理临时egg文件

    Args:
        project: The name of the project to set up the environment for.
                要为其设置环境的项目名称。

    Yields:
        None: This context manager doesn't yield a value, but sets up the
             environment for the code inside the with block.
             此上下文管理器不产生值，但为with块内的代码设置环境。

    Raises:
        AssertionError: If aioscrapy settings are already loaded.
                       如果aioscrapy设置已加载。
    """
    # Get the Scrapyd application and egg storage
    # 获取Scrapyd应用程序和egg存储
    app = get_application()
    eggstorage = app.getComponent(IEggStorage)

    # Get the egg version from environment or use the latest
    # 从环境获取egg版本或使用最新版本
    eggversion = os.environ.get('AIOSCRAPY_EGG_VERSION', None)

    # Get the egg file from storage
    # 从存储中获取egg文件
    version, eggfile = eggstorage.get(project, eggversion)

    if eggfile:
        # Create a temporary copy of the egg file
        # 创建egg文件的临时副本
        prefix = '%s-%s-' % (project, version)
        fd, eggpath = tempfile.mkstemp(prefix=prefix, suffix='.egg')
        lf = os.fdopen(fd, 'wb')
        shutil.copyfileobj(eggfile, lf)
        lf.close()

        # Activate the egg file
        # 激活egg文件
        activate_egg(eggpath)
    else:
        eggpath = None

    try:
        # Ensure settings aren't already loaded
        # 确保设置尚未加载
        assert 'aioscrapy.conf' not in sys.modules, "aioscrapy settings already loaded"
        yield
    finally:
        # Clean up the temporary egg file
        # 清理临时egg文件
        if eggpath:
            os.remove(eggpath)


def main():
    """
    Main entry point for running spiders from Scrapyd.
    从Scrapyd运行爬虫的主入口点。

    This function:
    此函数：

    1. Updates environment variables by converting SCRAPY_* variables to AIO* variables
       通过将SCRAPY_*变量转换为AIO*变量来更新环境变量
    2. Gets the project name from the AIOSCRAPY_PROJECT environment variable
       从AIOSCRAPY_PROJECT环境变量获取项目名称
    3. Sets up the project environment using the project_environment context manager
       使用project_environment上下文管理器设置项目环境
    4. Imports and executes the aioscrapy.cmdline.execute function to run the spider
       导入并执行aioscrapy.cmdline.execute函数来运行爬虫

    This function is designed to be called by Scrapyd to run AioScrapy spiders.
    此函数设计用于Scrapyd调用以运行AioScrapy爬虫。

    Raises:
        KeyError: If the AIOSCRAPY_PROJECT environment variable is not set.
                 如果未设置AIOSCRAPY_PROJECT环境变量。
    """
    # Update environment variables by converting SCRAPY_* to AIO*
    # 通过将SCRAPY_*转换为AIO*来更新环境变量
    os.environ.update({f'AIO{k}': v for k, v in os.environ.items() if k.startswith('SCRAPY_')})

    # Get the project name from environment
    # 从环境获取项目名称
    project = os.environ['AIOSCRAPY_PROJECT']

    # Set up the project environment and run the spider
    # 设置项目环境并运行爬虫
    with project_environment(project):
        from aioscrapy.cmdline import execute
        execute()


if __name__ == '__main__':
    main()
