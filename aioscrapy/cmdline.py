"""
Command Line Interface Module
命令行接口模块

This module provides the command-line interface for AioScrapy. It handles command
discovery, parsing command-line arguments, and executing commands.
此模块提供了AioScrapy的命令行接口。它处理命令发现、解析命令行参数和执行命令。

The main components are:
主要组件包括：

1. Command discovery functions: Find and load available commands
                              查找并加载可用命令
2. Command execution functions: Parse arguments and execute commands
                              解析参数并执行命令
3. Helper functions: Print help messages and handle errors
                   打印帮助消息并处理错误

Commands can be provided by:
命令可以由以下提供：

- Built-in commands in the aioscrapy.commands module
  aioscrapy.commands模块中的内置命令
- Entry points in the aioscrapy.commands group
  aioscrapy.commands组中的入口点
- Custom modules specified in the COMMANDS_MODULE setting
  COMMANDS_MODULE设置中指定的自定义模块
"""
import sys
import os
import optparse
import cProfile
import inspect
import pkg_resources

import aioscrapy
from aioscrapy.crawler import CrawlerProcess
from aioscrapy.commands import AioScrapyCommand
from aioscrapy.exceptions import UsageError
from aioscrapy.utils.misc import walk_modules
from aioscrapy.utils.project import inside_project, get_project_settings
from aioscrapy.utils.python import garbage_collect


def _iter_command_classes(module_name):
    """
    Iterate over all command classes in a module.
    迭代模块中的所有命令类。

    This function walks through all modules in the given module path and yields
    all classes that are subclasses of AioScrapyCommand and defined in the module
    (not imported).
    此函数遍历给定模块路径中的所有模块，并产生所有是AioScrapyCommand子类且在模块中
    定义（非导入）的类。

    Args:
        module_name: The name of the module to search for command classes.
                    要搜索命令类的模块名称。

    Yields:
        class: Command classes found in the module.
              在模块中找到的命令类。

    Note:
        TODO: add `name` attribute to commands and merge this function with
        aioscrapy.utils.spider.iter_spider_classes
    """
    # Walk through all modules in the given module path
    # 遍历给定模块路径中的所有模块
    for module in walk_modules(module_name):
        # Iterate over all objects in the module
        # 迭代模块中的所有对象
        for obj in vars(module).values():
            # Check if the object is a command class
            # 检查对象是否为命令类
            if (
                inspect.isclass(obj)
                and issubclass(obj, AioScrapyCommand)
                and obj.__module__ == module.__name__  # Only classes defined in this module
                                                      # 仅此模块中定义的类
                and not obj == AioScrapyCommand  # Exclude the base class
                                                # 排除基类
            ):
                yield obj


def _get_commands_from_module(module, inproject):
    """
    Get all commands from a module.
    从模块获取所有命令。

    This function creates a dictionary of command name -> command instance for all
    command classes found in the given module. It only includes commands that are
    available in the current context (either we're in a project, or the command
    doesn't require a project).
    此函数为在给定模块中找到的所有命令类创建一个命令名称 -> 命令实例的字典。它只包括
    在当前上下文中可用的命令（要么我们在项目中，要么命令不需要项目）。

    Args:
        module: The module name to search for commands.
               要搜索命令的模块名称。
        inproject: Whether we're currently inside a project.
                  我们当前是否在项目内。

    Returns:
        dict: A dictionary of command name -> command instance.
             命令名称 -> 命令实例的字典。
    """
    # Initialize an empty dictionary to store commands
    # 初始化一个空字典来存储命令
    d = {}

    # Iterate over all command classes in the module
    # 迭代模块中的所有命令类
    for cmd in _iter_command_classes(module):
        # Only include commands that are available in the current context
        # 只包括在当前上下文中可用的命令
        if inproject or not cmd.requires_project:
            # Use the last part of the module name as the command name
            # 使用模块名称的最后一部分作为命令名称
            cmdname = cmd.__module__.split('.')[-1]
            # Create an instance of the command class
            # 创建命令类的实例
            d[cmdname] = cmd()

    return d


def _get_commands_from_entry_points(inproject, group='aioscrapy.commands'):
    """
    Get commands from entry points.
    从入口点获取命令。

    This function loads commands from entry points in the specified group.
    Entry points allow third-party packages to provide AioScrapy commands.
    此函数从指定组中的入口点加载命令。入口点允许第三方包提供AioScrapy命令。

    Args:
        inproject: Whether we're currently inside a project.
                  我们当前是否在项目内。
                  This parameter is included for interface consistency with
                  _get_commands_from_module, but is not used in this implementation.
                  此参数包含是为了与_get_commands_from_module保持接口一致性，
                  但在此实现中未使用。
        group: The entry point group to search for commands.
              要搜索命令的入口点组。
              Defaults to 'aioscrapy.commands'.
              默认为'aioscrapy.commands'。

    Returns:
        dict: A dictionary of command name -> command instance.
             命令名称 -> 命令实例的字典。

    Raises:
        Exception: If an entry point doesn't point to a class.
                  如果入口点不指向类。
    """
    # Initialize an empty dictionary to store commands
    # 初始化一个空字典来存储命令
    cmds = {}

    # Iterate over all entry points in the specified group
    # 迭代指定组中的所有入口点
    for entry_point in pkg_resources.iter_entry_points(group):
        # Load the object from the entry point
        # 从入口点加载对象
        obj = entry_point.load()

        # Check if the object is a class
        # 检查对象是否为类
        if inspect.isclass(obj):
            # Create an instance of the class and add it to the commands dictionary
            # 创建类的实例并将其添加到命令字典中
            cmds[entry_point.name] = obj()
        else:
            # Raise an exception if the entry point doesn't point to a class
            # 如果入口点不指向类，则引发异常
            raise Exception(f"Invalid entry point {entry_point.name}")

    return cmds


def _get_commands_dict(settings, inproject):
    """
    Get a dictionary of all available commands.
    获取所有可用命令的字典。

    This function collects commands from three sources:
    此函数从三个来源收集命令：

    1. Built-in commands from the aioscrapy.commands module
       aioscrapy.commands模块中的内置命令
    2. Commands from entry points in the aioscrapy.commands group
       aioscrapy.commands组中的入口点命令
    3. Commands from the module specified in the COMMANDS_MODULE setting
       COMMANDS_MODULE设置中指定的模块中的命令

    Args:
        settings: The settings object.
                 设置对象。
        inproject: Whether we're currently inside a project.
                  我们当前是否在项目内。

    Returns:
        dict: A dictionary of command name -> command instance.
             命令名称 -> 命令实例的字典。
    """
    # Get built-in commands from the aioscrapy.commands module
    # 从aioscrapy.commands模块获取内置命令
    cmds = _get_commands_from_module('aioscrapy.commands', inproject)

    # Update with commands from entry points
    # 使用入口点中的命令更新
    cmds.update(_get_commands_from_entry_points(inproject))

    # Get the custom commands module from settings
    # 从设置获取自定义命令模块
    cmds_module = settings['COMMANDS_MODULE']

    # If a custom commands module is specified, add its commands
    # 如果指定了自定义命令模块，则添加其命令
    if cmds_module:
        cmds.update(_get_commands_from_module(cmds_module, inproject))

    return cmds


def _pop_command_name(argv):
    """
    Extract the command name from command line arguments.
    从命令行参数中提取命令名称。

    This function searches for the first argument that doesn't start with a dash,
    which is assumed to be the command name. It removes this argument from the
    list and returns it.
    此函数搜索第一个不以破折号开头的参数，该参数被假定为命令名称。它从列表中
    删除此参数并返回它。

    Args:
        argv: List of command line arguments.
             命令行参数列表。

    Returns:
        str or None: The command name if found, None otherwise.
                    如果找到，则为命令名称，否则为None。
    """
    # Start from index 0 (which corresponds to argv[1], the first argument after the script name)
    # 从索引0开始（对应于argv[1]，脚本名称之后的第一个参数）
    i = 0

    # Iterate through arguments, skipping the script name (argv[0])
    # 迭代参数，跳过脚本名称（argv[0]）
    for arg in argv[1:]:
        # If the argument doesn't start with a dash, it's the command name
        # 如果参数不以破折号开头，则它是命令名称
        if not arg.startswith('-'):
            # Remove the command name from the argument list
            # 从参数列表中删除命令名称
            del argv[i]
            # Return the command name
            # 返回命令名称
            return arg
        i += 1

    # No command name found
    # 未找到命令名称
    return None


def _print_header(settings, inproject):
    """
    Print the AioScrapy header with version and project information.
    打印带有版本和项目信息的AioScrapy标头。

    This function prints a header line showing the AioScrapy version and,
    if inside a project, the project name.
    此函数打印一个标头行，显示AioScrapy版本，如果在项目内，则显示项目名称。

    Args:
        settings: The settings object.
                 设置对象。
        inproject: Whether we're currently inside a project.
                  我们当前是否在项目内。
    """
    # Get the AioScrapy version
    # 获取AioScrapy版本
    version = aioscrapy.__version__

    # Print different headers depending on whether we're in a project
    # 根据我们是否在项目内打印不同的标头
    if inproject:
        print(f"ioscrapy {version} - project: {settings['BOT_NAME']}\n")
    else:
        print(f"Aioscrapy {version} - no active project\n")


def _print_commands(settings, inproject):
    """
    Print a list of available commands.
    打印可用命令列表。

    This function prints the AioScrapy header, usage information, and a list
    of all available commands with their short descriptions.
    此函数打印AioScrapy标头、使用信息和所有可用命令及其简短描述的列表。

    Args:
        settings: The settings object.
                 设置对象。
        inproject: Whether we're currently inside a project.
                  我们当前是否在项目内。
    """
    # Print the header
    # 打印标头
    _print_header(settings, inproject)

    # Print usage information
    # 打印使用信息
    print("Usage:")
    print("  aioscrapy <command> [options] [args]\n")

    # Print available commands
    # 打印可用命令
    print("Available commands:")
    cmds = _get_commands_dict(settings, inproject)
    for cmdname, cmdclass in sorted(cmds.items()):
        print(f"  {cmdname:<13} {cmdclass.short_desc()}")

    # If not in a project, mention that more commands are available in a project
    # 如果不在项目内，请提及在项目中有更多可用命令
    if not inproject:
        print()
        print("  [ more ]      More commands available when run from project directory")

    # Print help information
    # 打印帮助信息
    print()
    print('Use "aioscrapy <command> -h" to see more info about a command')


def _print_unknown_command(settings, cmdname, inproject):
    """
    Print an error message for an unknown command.
    打印未知命令的错误消息。

    This function prints the AioScrapy header and an error message indicating
    that the specified command is unknown.
    此函数打印AioScrapy标头和一条错误消息，指示指定的命令未知。

    Args:
        settings: The settings object.
                 设置对象。
        cmdname: The name of the unknown command.
                未知命令的名称。
        inproject: Whether we're currently inside a project.
                  我们当前是否在项目内。
    """
    # Print the header
    # 打印标头
    _print_header(settings, inproject)

    # Print error message
    # 打印错误消息
    print(f"Unknown command: {cmdname}\n")

    # Print help information
    # 打印帮助信息
    print('Use "aioscrapy" to see available commands')


def _run_print_help(parser, func, *a, **kw):
    """
    Run a function and handle UsageError exceptions.
    运行函数并处理UsageError异常。

    This function runs the specified function with the given arguments and handles
    UsageError exceptions by printing an error message and/or help information.
    此函数使用给定的参数运行指定的函数，并通过打印错误消息和/或帮助信息来处理
    UsageError异常。

    Args:
        parser: The option parser to use for printing help.
               用于打印帮助的选项解析器。
        func: The function to run.
             要运行的函数。
        *a: Positional arguments to pass to the function.
           传递给函数的位置参数。
        **kw: Keyword arguments to pass to the function.
             传递给函数的关键字参数。

    Raises:
        SystemExit: With exit code 2 if a UsageError occurs.
                   如果发生UsageError，则退出代码为2。
    """
    try:
        # Run the function with the given arguments
        # 使用给定的参数运行函数
        func(*a, **kw)
    except UsageError as e:
        # If the error has a message, print it
        # 如果错误有消息，则打印它
        if str(e):
            parser.error(str(e))

        # If the error requests help to be printed, print it
        # 如果错误请求打印帮助，则打印它
        if e.print_help:
            parser.print_help()

        # Exit with code 2 (command line syntax error)
        # 退出代码2（命令行语法错误）
        sys.exit(2)


def execute(argv=None, settings=None):
    """
    Main entry point for the AioScrapy command line interface.
    AioScrapy命令行接口的主入口点。

    This function parses command line arguments, finds the appropriate command,
    and runs it with the specified options and arguments.
    此函数解析命令行参数，找到适当的命令，并使用指定的选项和参数运行它。

    Args:
        argv: The command line arguments.
              命令行参数。
              Defaults to sys.argv.
              默认为sys.argv。
        settings: The settings object.
                 设置对象。
                 If None, the project settings will be used.
                 如果为None，则将使用项目设置。

    Raises:
        SystemExit: With exit code 0 if no command is specified,
                   or exit code 2 if an unknown command or a command that
                   requires a project is run outside a project.
                   如果未指定命令，则退出代码为0；
                   如果在项目外运行未知命令或需要项目的命令，则退出代码为2。
    """
    # Use sys.argv if no arguments are provided
    # 如果未提供参数，则使用sys.argv
    if argv is None:
        argv = sys.argv

    # Use project settings if no settings are provided
    # 如果未提供设置，则使用项目设置
    if settings is None:
        settings = get_project_settings()
        # Set EDITOR from environment if available
        # 如果可用，则从环境设置EDITOR
        try:
            editor = os.environ['EDITOR']
        except KeyError:
            pass
        else:
            settings['EDITOR'] = editor

    # Check if we're inside a project
    # 检查我们是否在项目内
    inproject = inside_project()

    # Get all available commands
    # 获取所有可用命令
    cmds = _get_commands_dict(settings, inproject)

    # Extract the command name from the arguments
    # 从参数中提取命令名称
    cmdname = _pop_command_name(argv)

    # Create an option parser
    # 创建选项解析器
    parser = optparse.OptionParser(formatter=optparse.TitledHelpFormatter(),
                                   conflict_handler='resolve')

    # If no command is specified, print the list of commands and exit
    # 如果未指定命令，则打印命令列表并退出
    if not cmdname:
        _print_commands(settings, inproject)
        sys.exit(0)
    # If the command is unknown, print an error message and exit
    # 如果命令未知，则打印错误消息并退出
    elif cmdname not in cmds:
        _print_unknown_command(settings, cmdname, inproject)
        sys.exit(2)

    # Get the command instance
    # 获取命令实例
    cmd = cmds[cmdname]

    # Set up the parser with command-specific information
    # 使用命令特定信息设置解析器
    parser.usage = f"aioscrapy {cmdname} {cmd.syntax()}"
    parser.description = cmd.long_desc()

    # Apply command-specific settings
    # 应用命令特定设置
    settings.setdict(cmd.default_settings, priority='command')
    cmd.settings = settings

    # Add command-specific options to the parser
    # 向解析器添加命令特定选项
    cmd.add_options(parser)

    # Parse the command line arguments
    # 解析命令行参数
    opts, args = parser.parse_args(args=argv[1:])

    # Process command options
    # 处理命令选项
    _run_print_help(parser, cmd.process_options, args, opts)

    # Set up the crawler process for the command
    # 为命令设置爬虫进程
    cmd.crawler_process = CrawlerProcess(settings)

    # Run the command and handle any usage errors
    # 运行命令并处理任何使用错误
    _run_print_help(parser, _run_command, cmd, args, opts)

    # Exit with the command's exit code
    # 使用命令的退出代码退出
    sys.exit(cmd.exitcode)


def _run_command(cmd, args, opts):
    """
    Run a command with the given arguments and options.
    使用给定的参数和选项运行命令。

    This function runs the command either with or without profiling,
    depending on the options.
    此函数根据选项运行命令，可以带有或不带有性能分析。

    Args:
        cmd: The command to run.
             要运行的命令。
        args: The arguments to pass to the command.
              传递给命令的参数。
        opts: The options to pass to the command.
              传递给命令的选项。
              Must have a 'profile' attribute that specifies whether to run
              with profiling.
              必须有一个'profile'属性，指定是否使用性能分析运行。
    """
    # If profiling is enabled, run the command with profiling
    # 如果启用了性能分析，则使用性能分析运行命令
    if opts.profile:
        _run_command_profiled(cmd, args, opts)
    else:
        # Otherwise, run the command directly
        # 否则，直接运行命令
        cmd.run(args, opts)


def _run_command_profiled(cmd, args, opts):
    """
    Run a command with profiling.
    使用性能分析运行命令。

    This function runs the command with cProfile profiling and optionally
    saves the profiling stats to a file.
    此函数使用cProfile性能分析运行命令，并可选择将性能分析统计信息保存到文件。

    Args:
        cmd: The command to run.
             要运行的命令。
        args: The arguments to pass to the command.
              传递给命令的参数。
        opts: The options to pass to the command.
              传递给命令的选项。
              Must have a 'profile' attribute that specifies the output file
              for profiling stats, or False to disable saving stats.
              必须有一个'profile'属性，指定性能分析统计信息的输出文件，
              或False以禁用保存统计信息。
    """
    # If a profile output file is specified, print a message
    # 如果指定了性能分析输出文件，则打印消息
    if opts.profile:
        sys.stderr.write(f"aioscrapy: writing cProfile stats to {opts.profile!r}\n")

    # Create a local namespace for the profiler
    # 为性能分析器创建本地命名空间
    loc = locals()

    # Create a profiler
    # 创建性能分析器
    p = cProfile.Profile()

    # Run the command with profiling
    # 使用性能分析运行命令
    p.runctx('cmd.run(args, opts)', globals(), loc)

    # If a profile output file is specified, save the stats
    # 如果指定了性能分析输出文件，则保存统计信息
    if opts.profile:
        p.dump_stats(opts.profile)


if __name__ == '__main__':
    try:
        execute('aioscrapy startproject test1'.split())
    finally:
        garbage_collect()
