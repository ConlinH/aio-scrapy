"""
Signal utility functions for aioscrapy.
aioscrapy的信号实用函数。

This module provides utility functions for working with signals in aioscrapy.
It includes functions for sending signals, catching and logging exceptions,
and managing signal connections.
此模块提供了用于处理aioscrapy中信号的实用函数。
它包括用于发送信号、捕获和记录异常以及管理信号连接的函数。
"""
import asyncio

from pydispatch.dispatcher import Anonymous, Any, disconnect, getAllReceivers, liveReceivers
from pydispatch.robustapply import robustApply

from aioscrapy.exceptions import StopDownload
from aioscrapy.utils.log import logger
from aioscrapy.utils.tools import create_task


class _IgnoredException(Exception):
    """
    Internal exception class used to mark exceptions that should be ignored in logs.
    内部异常类，用于标记应在日志中忽略的异常。

    This exception is used as a marker for exceptions that should not be logged
    when caught in signal handlers. It's used in conjunction with the 'dont_log'
    parameter in signal sending functions.
    此异常用作在信号处理程序中捕获时不应记录的异常的标记。
    它与信号发送函数中的'dont_log'参数一起使用。
    """
    pass


async def robustApplyWrap(f, recv, *args, **kw):
    """
    Wrap a function call with exception handling and async support.
    使用异常处理和异步支持包装函数调用。

    This function wraps the application of a function to a receiver with robust
    exception handling. It also supports awaiting coroutines returned by the function.
    If an exception occurs, it logs the error (unless the exception type is in dont_log)
    and returns the exception object instead of raising it.
    此函数使用健壮的异常处理包装函数对接收器的应用。它还支持等待函数返回的协程。
    如果发生异常，它会记录错误（除非异常类型在dont_log中），并返回异常对象而不是引发它。

    Args:
        f: The function to apply (typically robustApply).
           要应用的函数（通常是robustApply）。
        recv: The receiver object (signal handler).
              接收器对象（信号处理程序）。
        *args: Positional arguments to pass to the function.
               传递给函数的位置参数。
        **kw: Keyword arguments to pass to the function.
              传递给函数的关键字参数。
              Special keys:
              特殊键：
              - dont_log: Exception types to not log if caught.
                         如果捕获，不记录的异常类型。
              - spider: The spider instance (for context in logs).
                       爬虫实例（用于日志中的上下文）。

    Returns:
        The result of the function call, or the exception if one was caught.
        函数调用的结果，如果捕获到异常则返回异常。
    """
    # Extract special parameters
    # 提取特殊参数
    dont_log = kw.pop('dont_log', None)
    # Spider is kept in kw for context but extracted here for potential future use
    # 爬虫保留在kw中作为上下文，但在此提取以供将来使用
    spider = kw.get('spider', None)  # noqa: F841

    try:
        # Apply the function to the receiver
        # 将函数应用于接收器
        result = f(recv, *args, **kw)
        # If the result is a coroutine, await it
        # 如果结果是协程，等待它
        if asyncio.iscoroutine(result):
            return await result
        return result
    except (Exception, BaseException) as exc:  # noqa: E722
        # Log the exception unless it's a type we should ignore
        # 记录异常，除非它是我们应该忽略的类型
        if dont_log is None or not isinstance(exc, dont_log):
            logger.exception(f"Error caught on signal handler: {recv}")
        # Return the exception instead of raising it
        # 返回异常而不是引发它
        return exc


async def send_catch_log(signal=Any, sender=Anonymous, *arguments, **named):
    """
    Send a signal and catch any exceptions raised by handlers.
    发送信号并捕获处理程序引发的任何异常。

    This function is similar to pydispatcher.robust.sendRobust but with additional
    features for aioscrapy:
    1. It logs errors that occur in signal handlers
    2. It returns the exceptions instead of raising them
    3. It supports async signal handlers
    4. It has special handling for StopDownload exceptions

    此函数类似于pydispatcher.robust.sendRobust，但为aioscrapy提供了额外功能：
    1. 它记录信号处理程序中发生的错误
    2. 它返回异常而不是引发它们
    3. 它支持异步信号处理程序
    4. 它对StopDownload异常有特殊处理

    Args:
        signal: The signal to send. Default is Any (all signals).
               要发送的信号。默认为Any（所有信号）。
        sender: The sender of the signal. Default is Anonymous.
               信号的发送者。默认为Anonymous。
        *arguments: Positional arguments to pass to the signal handlers.
                   传递给信号处理程序的位置参数。
        **named: Keyword arguments to pass to the signal handlers.
                传递给信号处理程序的关键字参数。
                Special keys:
                特殊键：
                - dont_log: Exception types to not log if caught.
                           如果捕获，不记录的异常类型。

    Returns:
        list: A list of (receiver, result) tuples, where result is either the
              return value of the handler or the exception that was caught.
              (接收器, 结果)元组的列表，其中结果是处理程序的返回值或捕获的异常。
    """
    # Configure which exceptions should not be logged
    # 配置不应记录的异常
    named['dont_log'] = (named.pop('dont_log', _IgnoredException), StopDownload)

    # Collect responses from all receivers
    # 收集所有接收器的响应
    responses = []

    # Get all receivers for this signal and sender
    # 获取此信号和发送者的所有接收器
    for receiver in liveReceivers(getAllReceivers(sender, signal)):
        # Apply the handler function robustly, catching any exceptions
        # 健壮地应用处理程序函数，捕获任何异常
        result = await robustApplyWrap(
            robustApply,
            receiver,
            signal=signal,
            sender=sender,
            *arguments,
            **named
        )
        # Store the receiver and its result (or exception)
        # 存储接收器及其结果（或异常）
        responses.append((receiver, result))

    return responses


async def send_catch_log_deferred(signal=Any, sender=Anonymous, *arguments, **named):
    """
    Send a signal and gather results from all handlers concurrently.
    发送信号并同时收集所有处理程序的结果。

    This function is similar to send_catch_log but runs all signal handlers
    concurrently using asyncio tasks. It waits for all handlers to complete
    before returning the results.
    此函数类似于send_catch_log，但使用asyncio任务同时运行所有信号处理程序。
    它在返回结果之前等待所有处理程序完成。

    This is useful when signal handlers are independent of each other and
    can run in parallel, potentially improving performance.
    当信号处理程序彼此独立并且可以并行运行时，这很有用，可能会提高性能。

    Args:
        signal: The signal to send. Default is Any (all signals).
               要发送的信号。默认为Any（所有信号）。
        sender: The sender of the signal. Default is Anonymous.
               信号的发送者。默认为Anonymous。
        *arguments: Positional arguments to pass to the signal handlers.
                   传递给信号处理程序的位置参数。
        **named: Keyword arguments to pass to the signal handlers.
                传递给信号处理程序的关键字参数。

    Returns:
        list: A list of results from all signal handlers, in the order they were
              registered. Each result is either the return value of the handler
              or the exception that was caught.
              所有信号处理程序的结果列表，按它们注册的顺序排列。
              每个结果要么是处理程序的返回值，要么是捕获的异常。
    """
    # List to store tasks for each receiver
    # 用于存储每个接收器的任务的列表
    tasks = []

    # Get all receivers for this signal and sender
    # 获取此信号和发送者的所有接收器
    for receiver in liveReceivers(getAllReceivers(sender, signal)):
        # Create a task for each receiver to run concurrently
        # 为每个接收器创建一个任务以同时运行
        tasks.append(
            create_task(
                robustApplyWrap(
                    robustApply,
                    receiver,
                    signal=signal,
                    sender=sender,
                    *arguments,
                    **named
                )
            )
        )

    # Wait for all tasks to complete and return their results
    # 等待所有任务完成并返回它们的结果
    return await asyncio.gather(*tasks)


def disconnect_all(signal=Any, sender=Any):
    """
    Disconnect all signal handlers for a given signal and sender.
    断开给定信号和发送者的所有信号处理程序。

    This function disconnects all signal handlers that match the specified
    signal and sender. It's particularly useful for cleaning up after running
    tests to ensure that signal handlers from one test don't affect other tests.
    此函数断开与指定信号和发送者匹配的所有信号处理程序。
    它对于在运行测试后进行清理特别有用，以确保一个测试的信号处理程序不会影响其他测试。

    Args:
        signal: The signal to disconnect handlers from. Default is Any (all signals).
               要断开处理程序的信号。默认为Any（所有信号）。
        sender: The sender to disconnect handlers for. Default is Any (all senders).
               要断开处理程序的发送者。默认为Any（所有发送者）。

    Note:
        This function modifies the global signal registry maintained by PyDispatcher.
        此函数修改由PyDispatcher维护的全局信号注册表。
    """
    # Get all receivers for this signal and sender
    # 获取此信号和发送者的所有接收器
    for receiver in liveReceivers(getAllReceivers(sender, signal)):
        # Disconnect each receiver
        # 断开每个接收器
        disconnect(receiver, signal=signal, sender=sender)
