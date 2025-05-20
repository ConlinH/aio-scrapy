"""
Operating system signal utilities for aioscrapy.
aioscrapy的操作系统信号实用工具。

This module provides utilities for working with operating system signals in aioscrapy.
It includes functions for installing signal handlers and mapping between signal
numbers and their names.
此模块提供了用于处理aioscrapy中操作系统信号的实用工具。
它包括用于安装信号处理程序以及在信号编号和其名称之间映射的函数。
"""

import signal


# Dictionary mapping signal numbers to their names (e.g., {2: 'SIGINT', 15: 'SIGTERM'})
# 将信号编号映射到其名称的字典（例如，{2: 'SIGINT', 15: 'SIGTERM'}）
signal_names = {}

# Populate the signal_names dictionary by iterating through all attributes in the signal module
# 通过迭代信号模块中的所有属性来填充signal_names字典
for signame in dir(signal):
    # Only process attributes that start with 'SIG' but not 'SIG_'
    # (SIG_ prefixed constants are signal handlers, not signal types)
    # 只处理以'SIG'开头但不以'SIG_'开头的属性
    # （SIG_前缀的常量是信号处理程序，而不是信号类型）
    if signame.startswith('SIG') and not signame.startswith('SIG_'):
        # Get the signal number for this signal name
        # 获取此信号名称的信号编号
        signum = getattr(signal, signame)
        # Only add to the dictionary if it's an integer (a valid signal number)
        # 只有当它是整数（有效的信号编号）时才添加到字典中
        if isinstance(signum, int):
            signal_names[signum] = signame


def install_shutdown_handlers(function, override_sigint=True):
    """
    Install a function as a signal handler for common shutdown signals.
    为常见的关闭信号安装函数作为信号处理程序。

    This function installs the provided function as a handler for common shutdown
    signals such as SIGTERM (terminate), SIGINT (keyboard interrupt), and SIGBREAK
    (Ctrl-Break on Windows). This is useful for graceful shutdown of applications.
    此函数将提供的函数安装为常见关闭信号的处理程序，如SIGTERM（终止）、
    SIGINT（键盘中断）和SIGBREAK（Windows上的Ctrl-Break）。
    这对于应用程序的优雅关闭很有用。

    Args:
        function: The function to be called when a shutdown signal is received.
                 当收到关闭信号时要调用的函数。
                 This function should accept two parameters: signal number and frame.
                 此函数应接受两个参数：信号编号和帧。
        override_sigint: Whether to override an existing SIGINT handler.
                        是否覆盖现有的SIGINT处理程序。
                        If False, the SIGINT handler won't be installed if there's
                        already a custom handler in place (e.g., a debugger like Pdb).
                        如果为False，则在已有自定义处理程序（例如Pdb调试器）的情况下
                        不会安装SIGINT处理程序。
                        Defaults to True.
                        默认为True。

    Example:
        >>> def handle_shutdown(signum, frame):
        ...     print(f"Received signal {signal_names.get(signum, signum)}")
        ...     # Perform cleanup operations
        ...     sys.exit(0)
        >>> install_shutdown_handlers(handle_shutdown)
    """
    # Always install handler for SIGTERM (terminate signal)
    # 始终为SIGTERM（终止信号）安装处理程序
    signal.signal(signal.SIGTERM, function)

    # Install handler for SIGINT (keyboard interrupt) if:
    # - The current handler is the default handler, or
    # - override_sigint is True (forcing override of any existing handler)
    # 在以下情况下为SIGINT（键盘中断）安装处理程序：
    # - 当前处理程序是默认处理程序，或
    # - override_sigint为True（强制覆盖任何现有处理程序）
    if signal.getsignal(signal.SIGINT) == signal.default_int_handler or override_sigint:
        signal.signal(signal.SIGINT, function)

    # Install handler for SIGBREAK (Ctrl-Break) on Windows if available
    # 如果可用，在Windows上为SIGBREAK（Ctrl-Break）安装处理程序
    if hasattr(signal, 'SIGBREAK'):
        signal.signal(signal.SIGBREAK, function)
