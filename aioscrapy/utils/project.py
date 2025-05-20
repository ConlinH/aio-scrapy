"""
Project utility functions for aioscrapy.
aioscrapy的项目实用函数。

This module provides utility functions for working with aioscrapy projects.
It includes functions for determining if code is running inside a project,
accessing project data directories, and loading project settings.
此模块提供了用于处理aioscrapy项目的实用函数。
它包括用于确定代码是否在项目内运行、访问项目数据目录和加载项目设置的函数。
"""

import os
import warnings

from importlib import import_module
from os.path import join, dirname, abspath, isabs, exists

from aioscrapy.utils.conf import closest_aioscrapy_cfg, get_config, init_env
from aioscrapy.settings import Settings
from aioscrapy.exceptions import NotConfigured, AioScrapyDeprecationWarning


# Environment variable name that defines the settings module path
# 定义设置模块路径的环境变量名称
ENVVAR = 'AIOSCRAPY_SETTINGS_MODULE'

# Configuration section name for data directory settings in scrapy.cfg
# scrapy.cfg中数据目录设置的配置部分名称
DATADIR_CFG_SECTION = 'datadir'


def inside_project():
    """
    Check if the code is running inside an aioscrapy project.
    检查代码是否在aioscrapy项目内运行。

    This function determines if the current code is running inside an aioscrapy project
    by checking either:
    1. If the AIOSCRAPY_SETTINGS_MODULE environment variable is set and the module can be imported
    2. If a scrapy.cfg file can be found in the current directory or any parent directory

    此函数通过以下方式确定当前代码是否在aioscrapy项目内运行：
    1. 检查AIOSCRAPY_SETTINGS_MODULE环境变量是否设置且模块可以导入
    2. 检查当前目录或任何父目录中是否可以找到scrapy.cfg文件

    Returns:
        bool: True if running inside a project, False otherwise.
              如果在项目内运行则为True，否则为False。
    """
    # Check if the settings module environment variable is set
    # 检查是否设置了设置模块环境变量
    scrapy_module = os.environ.get('AIOSCRAPY_SETTINGS_MODULE')
    if scrapy_module is not None:
        try:
            # Try to import the settings module
            # 尝试导入设置模块
            import_module(scrapy_module)
        except ImportError as exc:
            # If import fails, warn but continue checking
            # 如果导入失败，发出警告但继续检查
            warnings.warn(f"Cannot import scrapy settings module {scrapy_module}: {exc}")
        else:
            # If import succeeds, we're inside a project
            # 如果导入成功，我们在项目内
            return True

    # If no settings module or import failed, check for scrapy.cfg file
    # 如果没有设置模块或导入失败，检查scrapy.cfg文件
    return bool(closest_aioscrapy_cfg())


def project_data_dir(project='default'):
    """
    Get the project data directory, creating it if it doesn't exist.
    获取项目数据目录，如果不存在则创建它。

    This function returns the path to the data directory for the specified project.
    The directory is determined in the following order:
    1. From the [datadir] section in scrapy.cfg if it exists
    2. Otherwise, defaults to a '.scrapy' directory in the same directory as scrapy.cfg

    此函数返回指定项目的数据目录的路径。
    目录按以下顺序确定：
    1. 如果存在，从scrapy.cfg的[datadir]部分获取
    2. 否则，默认为与scrapy.cfg相同目录中的'.scrapy'目录

    The function will create the directory if it doesn't exist.
    如果目录不存在，该函数将创建它。

    Args:
        project: The project name to get the data directory for.
                要获取数据目录的项目名称。
                Defaults to 'default'.
                默认为'default'。

    Returns:
        str: The absolute path to the project data directory.
             项目数据目录的绝对路径。

    Raises:
        NotConfigured: If not running inside a project or if scrapy.cfg cannot be found.
                      如果不在项目内运行或找不到scrapy.cfg。
    """
    # Check if we're inside a project
    # 检查我们是否在项目内
    if not inside_project():
        raise NotConfigured("Not inside a project")

    # Get the configuration
    # 获取配置
    cfg = get_config()

    # Try to get the data directory from the config
    # 尝试从配置中获取数据目录
    if cfg.has_option(DATADIR_CFG_SECTION, project):
        d = cfg.get(DATADIR_CFG_SECTION, project)
    else:
        # Fall back to default location
        # 回退到默认位置
        scrapy_cfg = closest_aioscrapy_cfg()
        if not scrapy_cfg:
            raise NotConfigured("Unable to find scrapy.cfg file to infer project data dir")
        d = abspath(join(dirname(scrapy_cfg), '.scrapy'))

    # Create the directory if it doesn't exist
    # 如果目录不存在，则创建它
    if not exists(d):
        os.makedirs(d)

    return d


def data_path(path, createdir=False):
    """
    Get the absolute path for a file within the project data directory.
    获取项目数据目录中文件的绝对路径。

    This function resolves a path relative to the project data directory.
    If the given path is already absolute, it returns it unmodified.
    If not inside a project, it uses a '.scrapy' directory in the current directory.

    此函数解析相对于项目数据目录的路径。
    如果给定的路径已经是绝对路径，则原样返回。
    如果不在项目内，则使用当前目录中的'.scrapy'目录。

    Args:
        path: The path to resolve. Can be absolute or relative.
              要解析的路径。可以是绝对路径或相对路径。
        createdir: Whether to create the directory if it doesn't exist.
                  如果目录不存在，是否创建它。
                  Defaults to False.
                  默认为False。

    Returns:
        str: The absolute path to the file or directory.
             文件或目录的绝对路径。
    """
    # If the path is not absolute, make it relative to the data directory
    # 如果路径不是绝对的，使其相对于数据目录
    if not isabs(path):
        if inside_project():
            # If inside a project, use the project data directory
            # 如果在项目内，使用项目数据目录
            path = join(project_data_dir(), path)
        else:
            # Otherwise, use a .scrapy directory in the current directory
            # 否则，使用当前目录中的.scrapy目录
            path = join('.scrapy', path)

    # Create the directory if requested and it doesn't exist
    # 如果请求且目录不存在，则创建目录
    if createdir and not exists(path):
        os.makedirs(path)

    return path


def get_project_settings():
    """
    Get a Settings instance with the project settings.
    获取包含项目设置的Settings实例。

    This function loads the project settings from the module specified in the
    AIOSCRAPY_SETTINGS_MODULE environment variable. If the variable is not set,
    it tries to initialize the environment using the project name from the
    AIOSCRAPY_PROJECT environment variable (defaulting to 'default').

    此函数从AIOSCRAPY_SETTINGS_MODULE环境变量指定的模块加载项目设置。
    如果未设置该变量，它会尝试使用AIOSCRAPY_PROJECT环境变量中的项目名称
    （默认为'default'）初始化环境。

    The function also handles environment variables prefixed with AIOSCRAPY_
    as a way to override settings, though this method is deprecated.

    该函数还处理以AIOSCRAPY_为前缀的环境变量作为覆盖设置的方式，
    尽管此方法已弃用。

    Returns:
        Settings: A Settings instance with the project settings loaded.
                 加载了项目设置的Settings实例。
    """
    # Initialize the environment if the settings module is not set
    # 如果未设置设置模块，则初始化环境
    if ENVVAR not in os.environ:
        project = os.environ.get('AIOSCRAPY_PROJECT', 'default')
        init_env(project)

    # Create a new Settings instance
    # 创建一个新的Settings实例
    settings = Settings()

    # Load settings from the module specified in the environment variable
    # 从环境变量指定的模块加载设置
    settings_module_path = os.environ.get(ENVVAR)
    if settings_module_path:
        settings.setmodule(settings_module_path, priority='project')

    # Get all environment variables prefixed with AIOSCRAPY_
    # 获取所有以AIOSCRAPY_为前缀的环境变量
    aioscrapy_envvars = {k[10:]: v for k, v in os.environ.items() if
                         k.startswith('AIOSCRAPY_')}

    # Define which environment variables are valid and not settings
    # 定义哪些环境变量是有效的且不是设置
    valid_envvars = {
        'CHECK',
        'PROJECT',
        'PYTHON_SHELL',
        'SETTINGS_MODULE',
    }

    # Find environment variables that are being used to override settings
    # 查找用于覆盖设置的环境变量
    setting_envvars = {k for k in aioscrapy_envvars if k not in valid_envvars}

    # Warn about deprecated usage of environment variables to override settings
    # 警告关于使用环境变量覆盖设置的已弃用用法
    if setting_envvars:
        setting_envvar_list = ', '.join(sorted(setting_envvars))
        warnings.warn(
            'Use of environment variables prefixed with AIOSCRAPY_ to override '
            'settings is deprecated. The following environment variables are '
            f'currently defined: {setting_envvar_list}',
            AioScrapyDeprecationWarning
        )

    # Apply the environment variable overrides
    # 应用环境变量覆盖
    settings.setdict(aioscrapy_envvars, priority='project')

    return settings
