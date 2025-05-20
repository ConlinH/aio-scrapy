"""
Configuration utilities for aioscrapy.
aioscrapy的配置实用工具。

This module provides utility functions for working with aioscrapy configuration.
It includes functions for handling component lists, command-line arguments,
finding configuration files, and processing feed export parameters.
此模块提供了用于处理aioscrapy配置的实用函数。
它包括用于处理组件列表、命令行参数、查找配置文件和处理Feed导出参数的函数。
"""

import numbers
import os
import sys
import warnings
from configparser import ConfigParser
from operator import itemgetter

from aioscrapy.exceptions import AioScrapyDeprecationWarning, UsageError

from aioscrapy.settings import BaseSettings
from aioscrapy.utils.deprecate import update_classpath
from aioscrapy.utils.python import without_none_values


def build_component_list(compdict, custom=None, convert=update_classpath):
    """
    Compose a component list from a dictionary mapping classes to their order.
    从将类映射到其顺序的字典中组合组件列表。

    This function builds an ordered list of components from a dictionary that maps
    component classes to their order values. Components with lower order values
    come first in the resulting list. Components with None values are excluded.
    此函数从将组件类映射到其顺序值的字典构建有序组件列表。
    具有较低顺序值的组件在结果列表中排在前面。值为None的组件将被排除。

    The function also handles class path updates through the convert function,
    which by default uses update_classpath to handle deprecated class paths.
    该函数还通过convert函数处理类路径更新，默认情况下使用update_classpath
    处理已弃用的类路径。

    Args:
        compdict: Dictionary mapping component classes to order values.
                 将组件类映射到顺序值的字典。
                 Values should be real numbers or None.
                 值应为实数或None。
        custom: Additional components to include, either as a dictionary to update
               compdict, or as a list/tuple of components (for backward compatibility).
               要包含的其他组件，可以是用于更新compdict的字典，
               也可以是组件的列表/元组（用于向后兼容性）。
               Defaults to None.
               默认为None。
        convert: Function to convert/update class paths.
                用于转换/更新类路径的函数。
                Defaults to update_classpath.
                默认为update_classpath。

    Returns:
        list: Ordered list of component classes.
              有序的组件类列表。

    Raises:
        ValueError: If multiple component paths convert to the same object,
                   or if a component value is not a real number or None.
                   如果多个组件路径转换为同一对象，
                   或者如果组件值不是实数或None。
    """
    def _check_components(complist):
        """
        Check that no two components in the list convert to the same object.
        检查列表中没有两个组件转换为同一对象。
        """
        if len({convert(c) for c in complist}) != len(complist):
            raise ValueError(f'Some paths in {complist!r} convert to the same object, '
                             'please update your settings')

    def _map_keys(compdict):
        """
        Convert all keys in the component dictionary using the convert function.
        使用convert函数转换组件字典中的所有键。

        Handles both BaseSettings objects and regular dictionaries.
        处理BaseSettings对象和常规字典。
        """
        if isinstance(compdict, BaseSettings):
            compbs = BaseSettings()
            for k, v in compdict.items():
                prio = compdict.getpriority(k)
                if compbs.getpriority(convert(k)) == prio:
                    raise ValueError(f'Some paths in {list(compdict.keys())!r} '
                                     'convert to the same '
                                     'object, please update your settings'
                                     )
                else:
                    compbs.set(convert(k), v, priority=prio)
            return compbs
        else:
            _check_components(compdict)
            return {convert(k): v for k, v in compdict.items()}

    def _validate_values(compdict):
        """
        Fail if a value in the components dict is not a real number or None.
        如果组件字典中的值不是实数或None，则失败。
        """
        for name, value in compdict.items():
            if value is not None and not isinstance(value, numbers.Real):
                raise ValueError(f'Invalid value {value} for component {name}, '
                                 'please provide a real number or None instead')

    # BEGIN Backward compatibility for old (base, custom) call signature
    # 开始向后兼容旧的(base, custom)调用签名
    if isinstance(custom, (list, tuple)):
        _check_components(custom)
        return type(custom)(convert(c) for c in custom)

    if custom is not None:
        compdict.update(custom)
    # END Backward compatibility
    # 结束向后兼容

    # Validate all values in the dictionary
    # 验证字典中的所有值
    _validate_values(compdict)

    # Convert keys and remove None values
    # 转换键并删除None值
    compdict = without_none_values(_map_keys(compdict))

    # Sort components by their order values and return just the component classes
    # 按组件的顺序值排序，并仅返回组件类
    return [k for k, v in sorted(compdict.items(), key=itemgetter(1))]


def arglist_to_dict(arglist):
    """
    Convert a list of key=value arguments to a dictionary.
    将key=value参数列表转换为字典。

    This function takes a list of strings in the format 'key=value' and converts
    them into a dictionary where each key is mapped to its corresponding value.
    此函数接受格式为'key=value'的字符串列表，并将它们转换为字典，
    其中每个键都映射到其对应的值。

    Args:
        arglist: List of strings in the format 'key=value'.
                格式为'key=value'的字符串列表。
                Example: ['arg1=val1', 'arg2=val2', ...]
                示例：['arg1=val1', 'arg2=val2', ...]

    Returns:
        dict: Dictionary mapping keys to values.
              将键映射到值的字典。
              Example: {'arg1': 'val1', 'arg2': 'val2', ...}
              示例：{'arg1': 'val1', 'arg2': 'val2', ...}

    Raises:
        ValueError: If any string in the list doesn't contain an equals sign.
                   如果列表中的任何字符串不包含等号。
    """
    # Split each string at the first equals sign and convert to a dictionary
    # 在第一个等号处分割每个字符串并转换为字典
    return dict(x.split('=', 1) for x in arglist)


def closest_aioscrapy_cfg(path='.', prevpath=None):
    """
    Find the closest aioscrapy.cfg file by traversing up the directory tree.
    通过向上遍历目录树查找最近的aioscrapy.cfg文件。

    This function searches for an aioscrapy.cfg file in the specified directory
    and its parent directories. It starts from the given path and moves up the
    directory tree until it finds a configuration file or reaches the root directory.
    此函数在指定目录及其父目录中搜索aioscrapy.cfg文件。
    它从给定路径开始，向上移动目录树，直到找到配置文件或到达根目录。

    Args:
        path: Directory path to start the search from.
              开始搜索的目录路径。
              Defaults to the current directory ('.').
              默认为当前目录('.')。
        prevpath: Path from the previous recursive call, used to detect when we've
                 reached the root directory.
                 上一个递归调用的路径，用于检测何时到达根目录。
                 Defaults to None.
                 默认为None。

    Returns:
        str: Absolute path to the closest aioscrapy.cfg file, or an empty string
             if no configuration file is found.
             最近的aioscrapy.cfg文件的绝对路径，如果未找到配置文件，则为空字符串。
    """
    # If we've reached the root directory (path doesn't change between iterations)
    # 如果我们已经到达根目录（路径在迭代之间没有变化）
    if path == prevpath:
        return ''

    # Convert to absolute path to ensure consistent behavior
    # 转换为绝对路径以确保一致的行为
    path = os.path.abspath(path)

    # Check if aioscrapy.cfg exists in the current directory
    # 检查当前目录中是否存在aioscrapy.cfg
    cfgfile = os.path.join(path, 'aioscrapy.cfg')
    if os.path.exists(cfgfile):
        return cfgfile

    # Recursively check the parent directory
    # 递归检查父目录
    return closest_aioscrapy_cfg(os.path.dirname(path), path)


def init_env(project='default', set_syspath=True):
    """
    Initialize environment for running aioscrapy from inside a project directory.
    初始化环境，以便从项目目录内运行aioscrapy。

    This function sets up the environment for running aioscrapy commands from within
    a project directory. It:
    1. Sets the AIOSCRAPY_SETTINGS_MODULE environment variable based on the project
    2. Adds the project directory to sys.path if needed

    此函数设置环境，以便从项目目录内运行aioscrapy命令。它：
    1. 根据项目设置AIOSCRAPY_SETTINGS_MODULE环境变量
    2. 如果需要，将项目目录添加到sys.path

    Args:
        project: The project name to use for settings lookup in scrapy.cfg.
                用于在scrapy.cfg中查找设置的项目名称。
                Defaults to 'default'.
                默认为'default'。
        set_syspath: Whether to add the project directory to sys.path.
                    是否将项目目录添加到sys.path。
                    Defaults to True.
                    默认为True。
    """
    # Get the configuration from scrapy.cfg
    # 从scrapy.cfg获取配置
    cfg = get_config()

    # Set the settings module environment variable if defined in the config
    # 如果在配置中定义，则设置设置模块环境变量
    if cfg.has_option('settings', project):
        os.environ['AIOSCRAPY_SETTINGS_MODULE'] = cfg.get('settings', project)

    # Find the closest aioscrapy.cfg file
    # 查找最近的aioscrapy.cfg文件
    closest = closest_aioscrapy_cfg()

    # If a config file was found, add its directory to sys.path if needed
    # 如果找到配置文件，则在需要时将其目录添加到sys.path
    if closest:
        projdir = os.path.dirname(closest)
        if set_syspath and projdir not in sys.path:
            sys.path.append(projdir)


def get_config(use_closest=True):
    """
    Get aioscrapy configuration as a ConfigParser object.
    获取aioscrapy配置作为ConfigParser对象。

    This function reads the aioscrapy configuration from various possible locations
    and returns it as a ConfigParser object. By default, it looks for configuration
    in standard system locations and the closest aioscrapy.cfg file in the current
    directory or its parents.
    此函数从各种可能的位置读取aioscrapy配置，并将其作为ConfigParser对象返回。
    默认情况下，它在标准系统位置和当前目录或其父目录中最近的aioscrapy.cfg文件中
    查找配置。

    Args:
        use_closest: Whether to include the closest aioscrapy.cfg file in the
                    configuration sources.
                    是否在配置源中包含最近的aioscrapy.cfg文件。
                    Defaults to True.
                    默认为True。

    Returns:
        ConfigParser: A ConfigParser object with the loaded configuration.
                     加载了配置的ConfigParser对象。
    """
    # Get the list of configuration file paths to read
    # 获取要读取的配置文件路径列表
    sources = get_sources(use_closest)

    # Create a new ConfigParser and read the configuration files
    # 创建一个新的ConfigParser并读取配置文件
    cfg = ConfigParser()
    cfg.read(sources)

    return cfg


def get_sources(use_closest=True):
    """
    Get a list of possible configuration file paths.
    获取可能的配置文件路径列表。

    This function returns a list of paths where aioscrapy configuration files might
    be located. It includes standard system locations and optionally the closest
    aioscrapy.cfg file in the current directory or its parents.
    此函数返回可能位于aioscrapy配置文件的路径列表。它包括标准系统位置，
    以及可选的当前目录或其父目录中最近的aioscrapy.cfg文件。

    The function looks for configuration files in the following locations:
    该函数在以下位置查找配置文件：
    1. /etc/scrapy.cfg (Unix system-wide)
    2. c:\\scrapy\\scrapy.cfg (Windows system-wide)
    3. $XDG_CONFIG_HOME/scrapy.cfg (or ~/.config/scrapy.cfg)
    4. ~/.scrapy.cfg (user home directory)
    5. The closest aioscrapy.cfg file (if use_closest is True)

    Args:
        use_closest: Whether to include the closest aioscrapy.cfg file in the
                    returned list.
                    是否在返回的列表中包含最近的aioscrapy.cfg文件。
                    Defaults to True.
                    默认为True。

    Returns:
        list: A list of file paths to check for configuration.
              要检查配置的文件路径列表。
    """
    # Get XDG config home directory (Linux standard) or default to ~/.config
    # 获取XDG配置主目录（Linux标准）或默认为~/.config
    xdg_config_home = os.environ.get('XDG_CONFIG_HOME') or os.path.expanduser('~/.config')

    # List of standard locations to check for configuration files
    # 检查配置文件的标准位置列表
    sources = [
        '/etc/scrapy.cfg',              # Unix system-wide
        r'c:\scrapy\scrapy.cfg',        # Windows system-wide
        xdg_config_home + '/scrapy.cfg', # XDG config directory
        os.path.expanduser('~/.scrapy.cfg'), # User home directory
    ]

    # Optionally add the closest aioscrapy.cfg file
    # 可选地添加最近的aioscrapy.cfg文件
    if use_closest:
        sources.append(closest_aioscrapy_cfg())

    return sources


def feed_complete_default_values_from_settings(feed, settings):
    """
    Complete feed export configuration with default values from settings.
    使用设置中的默认值完成Feed导出配置。

    This function takes a feed export configuration dictionary and fills in any
    missing values with defaults from the project settings. It creates a new
    dictionary without modifying the original.
    此函数接受Feed导出配置字典，并使用项目设置中的默认值填充任何缺失的值。
    它创建一个新字典，而不修改原始字典。

    The following feed export settings are handled:
    处理以下Feed导出设置：
    - batch_item_count: Number of items per batch
    - encoding: Character encoding for the exported data
    - fields: List of fields to export
    - store_empty: Whether to store empty feeds
    - uri_params: Parameters for URI formatting
    - item_export_kwargs: Additional keyword arguments for item export
    - indent: Indentation level for formatted outputs

    Args:
        feed: Original feed export configuration dictionary.
              原始Feed导出配置字典。
        settings: Project settings object.
                 项目设置对象。

    Returns:
        dict: A new dictionary with the feed export configuration, including
              defaults for any missing values.
              包含Feed导出配置的新字典，包括任何缺失值的默认值。
    """
    # Create a copy of the original feed dictionary to avoid modifying it
    # 创建原始feed字典的副本，以避免修改它
    out = feed.copy()

    # Set default values for all feed export settings from the project settings
    # 从项目设置中为所有Feed导出设置设置默认值
    out.setdefault("batch_item_count", settings.getint('FEED_EXPORT_BATCH_ITEM_COUNT'))
    out.setdefault("encoding", settings["FEED_EXPORT_ENCODING"])
    out.setdefault("fields", settings.getlist("FEED_EXPORT_FIELDS") or None)
    out.setdefault("store_empty", settings.getbool("FEED_STORE_EMPTY"))
    out.setdefault("uri_params", settings["FEED_URI_PARAMS"])
    out.setdefault("item_export_kwargs", dict())

    # Handle indentation specially since it might be None
    # 特别处理缩进，因为它可能是None
    if settings["FEED_EXPORT_INDENT"] is None:
        out.setdefault("indent", None)
    else:
        out.setdefault("indent", settings.getint("FEED_EXPORT_INDENT"))

    return out


def feed_process_params_from_cli(settings, output, output_format=None,
                                 overwrite_output=None):
    """
    Process feed export parameters from command-line arguments.
    处理来自命令行参数的Feed导出参数。

    This function processes feed export parameters provided via command-line arguments
    (from the 'crawl' or 'runspider' commands), checks for inconsistencies, and
    returns a dictionary suitable to be used as the FEEDS setting.
    此函数处理通过命令行参数提供的Feed导出参数（来自'crawl'或'runspider'命令），
    检查不一致性，并返回一个适合用作FEEDS设置的字典。

    It handles:
    它处理：
    - Output URIs (-o/--output or -O/--overwrite-output options)
    - Output format (-t option, deprecated)
    - Format specified in the URI (e.g., file.json:json)
    - Format inferred from file extension (e.g., file.json)
    - Overwrite flag (-O/--overwrite-output option)

    Args:
        settings: Project settings object.
                 项目设置对象。
        output: List of output URIs from -o/--output options.
               来自-o/--output选项的输出URI列表。
        output_format: Output format from -t option (deprecated).
                      来自-t选项的输出格式（已弃用）。
                      Defaults to None.
                      默认为None。
        overwrite_output: List of output URIs from -O/--overwrite-output options.
                         来自-O/--overwrite-output选项的输出URI列表。
                         Defaults to None.
                         默认为None。

    Returns:
        dict: A dictionary suitable for use as the FEEDS setting.
              适合用作FEEDS设置的字典。

    Raises:
        UsageError: If there are inconsistencies in the provided parameters.
                   如果提供的参数中存在不一致。
    """
    # Get the list of valid output formats from settings
    # 从设置中获取有效输出格式的列表
    valid_output_formats = without_none_values(
        settings.getwithbase('FEED_EXPORTERS')
    ).keys()

    def check_valid_format(output_format):
        """
        Check if the output format is valid and raise an error if not.
        检查输出格式是否有效，如果无效则引发错误。
        """
        if output_format not in valid_output_formats:
            raise UsageError(
                f"Unrecognized output format '{output_format}'. "
                f"Set a supported one ({tuple(valid_output_formats)}) "
                "after a colon at the end of the output URI (i.e. -o/-O "
                "<URI>:<FORMAT>) or as a file extension."
            )

    # Handle -O/--overwrite-output option
    # 处理-O/--overwrite-output选项
    overwrite = False
    if overwrite_output:
        if output:
            raise UsageError(
                "Please use only one of -o/--output and -O/--overwrite-output"
            )
        output = overwrite_output
        overwrite = True

    # Handle -t option (deprecated)
    # 处理-t选项（已弃用）
    if output_format:
        if len(output) == 1:
            check_valid_format(output_format)
            message = (
                'The -t command line option is deprecated in favor of '
                'specifying the output format within the output URI. See the '
                'documentation of the -o and -O options for more information.',
            )
            warnings.warn(message, AioScrapyDeprecationWarning, stacklevel=2)
            return {output[0]: {'format': output_format}}
        else:
            raise UsageError(
                'The -t command-line option cannot be used if multiple output '
                'URIs are specified'
            )

    # Process each output URI
    # 处理每个输出URI
    result = {}
    for element in output:
        # Try to extract format from URI (e.g., file.json:json)
        # 尝试从URI中提取格式（例如，file.json:json）
        try:
            feed_uri, feed_format = element.rsplit(':', 1)
        except ValueError:
            # If no format in URI, infer from file extension
            # 如果URI中没有格式，从文件扩展名推断
            feed_uri = element
            feed_format = os.path.splitext(element)[1].replace('.', '')
        else:
            # Special case for stdout
            # stdout的特殊情况
            if feed_uri == '-':
                feed_uri = 'stdout:'

        # Validate the format
        # 验证格式
        check_valid_format(feed_format)

        # Add to result dictionary
        # 添加到结果字典
        result[feed_uri] = {'format': feed_format}
        if overwrite:
            result[feed_uri]['overwrite'] = True

    # FEEDS setting should take precedence over the matching CLI options
    # FEEDS设置应优先于匹配的CLI选项
    result.update(settings.getdict('FEEDS'))

    return result
