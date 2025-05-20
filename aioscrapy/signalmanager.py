"""
Signal Manager for AioScrapy
AioScrapy的信号管理器

This module provides the SignalManager class which is responsible for coordinating
signals and receivers in the AioScrapy framework. It wraps PyDispatcher to provide
a more convenient API for connecting, disconnecting, and sending signals.
此模块提供了SignalManager类，负责协调AioScrapy框架中的信号和接收器。
它封装了PyDispatcher，提供了更方便的API用于连接、断开和发送信号。
"""

from pydispatch import dispatcher
from aioscrapy.utils import signal as _signal


class SignalManager:
    """
    Class for managing signals in AioScrapy.
    用于管理AioScrapy中信号的类。

    This class provides methods to connect and disconnect receivers to signals,
    as well as to send signals with proper exception handling. It serves as a
    wrapper around PyDispatcher, providing a more convenient API for AioScrapy.
    此类提供了将接收器连接到信号和断开连接的方法，以及发送带有适当异常处理的信号的方法。
    它作为PyDispatcher的包装器，为AioScrapy提供了更方便的API。
    """

    def __init__(self, sender=dispatcher.Anonymous):
        """
        Initialize a SignalManager.
        初始化一个SignalManager。

        Args:
            sender: The default sender to use when connecting or sending signals.
                   连接或发送信号时使用的默认发送者。
                   Defaults to dispatcher.Anonymous, which is a special object
                   used to identify anonymous senders.
                   默认为dispatcher.Anonymous，这是一个用于标识匿名发送者的特殊对象。
        """
        self.sender = sender

    def connect(self, receiver, signal, **kwargs):
        """
        Connect a receiver function to a signal.
        将接收器函数连接到信号。

        This method connects a receiver function to a signal so that the function
        is called when the signal is sent. The receiver function will receive the
        signal object and any additional keyword arguments passed when the signal
        is sent.
        此方法将接收器函数连接到信号，以便在发送信号时调用该函数。
        接收器函数将接收信号对象和发送信号时传递的任何其他关键字参数。

        Args:
            receiver: The function to be connected to the signal.
                     要连接到信号的函数。
                     This function will be called when the signal is sent.
                     当信号发送时，将调用此函数。
            signal: The signal to connect to.
                   要连接的信号。
                   This can be any object, although AioScrapy comes with predefined
                   signals in the aioscrapy.signals module.
                   这可以是任何对象，尽管AioScrapy在aioscrapy.signals模块中
                   提供了预定义的信号。
            **kwargs: Additional keyword arguments to pass to PyDispatcher's connect.
                     传递给PyDispatcher的connect的其他关键字参数。

        Returns:
            bool: True if the receiver was successfully connected, False otherwise.
                 如果接收器成功连接，则为True，否则为False。
        """
        # Set the default sender if not provided
        # 如果未提供，则设置默认发送者
        kwargs.setdefault('sender', self.sender)
        # Connect the receiver to the signal using PyDispatcher
        # 使用PyDispatcher将接收器连接到信号
        return dispatcher.connect(receiver, signal, **kwargs)

    def disconnect(self, receiver, signal, **kwargs):
        """
        Disconnect a receiver function from a signal.
        断开接收器函数与信号的连接。

        This method disconnects a previously connected receiver function from a signal.
        It has the opposite effect of the connect method, and the arguments are the same.
        此方法断开先前连接到信号的接收器函数。
        它具有与connect方法相反的效果，参数相同。

        Args:
            receiver: The function to be disconnected from the signal.
                     要从信号断开连接的函数。
            signal: The signal to disconnect from.
                   要断开连接的信号。
            **kwargs: Additional keyword arguments to pass to PyDispatcher's disconnect.
                     传递给PyDispatcher的disconnect的其他关键字参数。

        Returns:
            bool: True if the receiver was successfully disconnected, False otherwise.
                 如果接收器成功断开连接，则为True，否则为False。
                 False might indicate that the receiver was not connected to the signal.
                 False可能表示接收器未连接到信号。
        """
        # Set the default sender if not provided
        # 如果未提供，则设置默认发送者
        kwargs.setdefault('sender', self.sender)
        # Disconnect the receiver from the signal using PyDispatcher
        # 使用PyDispatcher断开接收器与信号的连接
        return dispatcher.disconnect(receiver, signal, **kwargs)

    async def send_catch_log(self, signal, **kwargs):
        """
        Send a signal, catch exceptions and log them.
        发送信号，捕获异常并记录它们。

        This method sends a signal to all connected receivers. If a receiver raises
        an exception, it is caught and logged, but the signal continues to be sent
        to other receivers. This ensures that one failing receiver doesn't prevent
        other receivers from receiving the signal.
        此方法向所有连接的接收器发送信号。如果接收器引发异常，
        则会捕获并记录该异常，但信号继续发送给其他接收器。
        这确保一个失败的接收器不会阻止其他接收器接收信号。

        Args:
            signal: The signal to send.
                   要发送的信号。
            **kwargs: Keyword arguments to pass to the signal handlers.
                     传递给信号处理程序的关键字参数。

        Returns:
            list: A list of (receiver, response) tuples, where response is either
                 the return value of the handler or the exception that was caught.
                 (接收器, 响应)元组的列表，其中响应是处理程序的返回值或捕获的异常。
        """
        # Set the default sender if not provided
        # 如果未提供，则设置默认发送者
        kwargs.setdefault('sender', self.sender)
        # Send the signal using the utility function from aioscrapy.utils.signal
        # 使用aioscrapy.utils.signal中的实用函数发送信号
        return await _signal.send_catch_log(signal, **kwargs)

    async def send_catch_log_deferred(self, signal, **kwargs):
        """
        Send a signal and gather results from all handlers concurrently.
        发送信号并同时收集所有处理程序的结果。

        This method is similar to send_catch_log but runs all signal handlers
        concurrently using asyncio tasks. It waits for all handlers to complete
        before returning the results. This is useful when signal handlers are
        independent of each other and can run in parallel.
        此方法类似于send_catch_log，但使用asyncio任务同时运行所有信号处理程序。
        它在返回结果之前等待所有处理程序完成。当信号处理程序彼此独立并且
        可以并行运行时，这很有用。

        Args:
            signal: The signal to send.
                   要发送的信号。
            **kwargs: Keyword arguments to pass to the signal handlers.
                     传递给信号处理程序的关键字参数。

        Returns:
            list: A list of results from all signal handlers, in the order they were
                 registered. Each result is either the return value of the handler
                 or the exception that was caught.
                 所有信号处理程序的结果列表，按它们注册的顺序排列。
                 每个结果要么是处理程序的返回值，要么是捕获的异常。
        """
        # Set the default sender if not provided
        # 如果未提供，则设置默认发送者
        kwargs.setdefault('sender', self.sender)
        # Send the signal using the utility function from aioscrapy.utils.signal
        # 使用aioscrapy.utils.signal中的实用函数发送信号
        return await _signal.send_catch_log_deferred(signal, **kwargs)

    def disconnect_all(self, signal, **kwargs):
        """
        Disconnect all receivers from the given signal.
        断开给定信号的所有接收器。

        This method disconnects all receivers that are connected to the specified
        signal. It's useful for cleaning up signal connections, especially during
        testing or when shutting down a component.
        此方法断开连接到指定信号的所有接收器。
        它对于清理信号连接很有用，特别是在测试期间或关闭组件时。

        Args:
            signal: The signal to disconnect all receivers from.
                   要断开所有接收器的信号。
            **kwargs: Additional keyword arguments to pass to the disconnect_all function.
                     传递给disconnect_all函数的其他关键字参数。

        Returns:
            None
        """
        # Set the default sender if not provided
        # 如果未提供，则设置默认发送者
        kwargs.setdefault('sender', self.sender)
        # Disconnect all receivers using the utility function from aioscrapy.utils.signal
        # 使用aioscrapy.utils.signal中的实用函数断开所有接收器
        return _signal.disconnect_all(signal, **kwargs)
