"""
Abstract Middleware Manager Module
抽象中间件管理器模块

This module provides the abstract base class for middleware managers in AioScrapy.
Middleware managers are responsible for loading, organizing, and executing middleware
components in the correct order during the request/response processing cycle.
此模块提供了AioScrapy中间件管理器的抽象基类。中间件管理器负责在请求/响应处理
周期中以正确的顺序加载、组织和执行中间件组件。

Concrete implementations of this abstract class include the DownloaderMiddlewareManager
and SpiderMiddlewareManager classes.
此抽象类的具体实现包括DownloaderMiddlewareManager和SpiderMiddlewareManager类。
"""
import pprint
from abc import ABCMeta, abstractmethod
from collections import defaultdict, deque

from aioscrapy.exceptions import NotConfigured
from aioscrapy.utils.log import logger
from aioscrapy.utils.misc import load_instance
from aioscrapy.utils.tools import call_helper


class AbsMiddlewareManager(object, metaclass=ABCMeta):
    """
    Abstract base class for implementing middleware managers.
    实现中间件管理器的抽象基类。

    This class provides the common functionality for managing middleware components,
    including loading middleware from settings, organizing them in the correct order,
    and executing their methods during the request/response processing cycle.
    此类提供了管理中间件组件的通用功能，包括从设置加载中间件、以正确的顺序组织它们，
    以及在请求/响应处理周期中执行它们的方法。

    Concrete subclasses must implement the _get_mwlist_from_settings method to
    specify how to retrieve the middleware list from settings.
    具体子类必须实现_get_mwlist_from_settings方法，以指定如何从设置中检索中间件列表。
    """

    # Name of the middleware component, to be overridden by subclasses
    # 中间件组件的名称，由子类覆盖
    component_name = 'foo middleware'

    def __init__(self, *middlewares):
        """
        Initialize the middleware manager with a list of middleware instances.
        使用中间件实例列表初始化中间件管理器。

        Args:
            *middlewares: Variable length list of middleware instances.
                         可变长度的中间件实例列表。
        """
        # Store the middleware instances
        # 存储中间件实例
        self.middlewares = middlewares

        # Dictionary to store middleware methods by name
        # 按名称存储中间件方法的字典
        self.methods = defaultdict(deque)

        # Add each middleware to the manager
        # 将每个中间件添加到管理器
        for mw in middlewares:
            self._add_middleware(mw)

    @classmethod
    @abstractmethod
    def _get_mwlist_from_settings(cls, settings):
        """
        Get middleware list from settings.
        从设置中获取中间件列表。

        This abstract method must be implemented by subclasses to specify
        how to retrieve the middleware list from the settings object.
        此抽象方法必须由子类实现，以指定如何从设置对象中检索中间件列表。

        Args:
            settings: The settings object.
                     设置对象。

        Returns:
            list: A list of middleware class paths.
                 中间件类路径列表。
        """
        pass

    @classmethod
    async def from_settings(cls, settings, crawler=None):
        """
        Create a middleware manager from settings.
        从设置创建中间件管理器。

        This method loads middleware instances from the settings object and
        creates a new middleware manager with those instances.
        此方法从设置对象加载中间件实例，并使用这些实例创建新的中间件管理器。

        Args:
            settings: The settings object.
                     设置对象。
            crawler: Optional crawler instance.
                    可选的爬虫实例。
                    Defaults to None.
                    默认为None。

        Returns:
            AbsMiddlewareManager: A new middleware manager instance.
                                 新的中间件管理器实例。
        """
        # Get middleware list from settings
        # 从设置中获取中间件列表
        mwlist = cls._get_mwlist_from_settings(settings)

        # Lists to store loaded middleware instances and enabled middleware paths
        # 用于存储已加载的中间件实例和已启用的中间件路径的列表
        middlewares = []
        enabled = []

        # Load each middleware
        # 加载每个中间件
        for clspath in mwlist:
            try:
                # Load the middleware instance
                # 加载中间件实例
                middlewares.append(await load_instance(clspath, settings=settings, crawler=crawler))

                # Add to enabled list
                # 添加到已启用列表
                enabled.append(clspath)
            except NotConfigured as e:
                # Log warning if middleware is disabled with a reason
                # 如果中间件因某种原因被禁用，则记录警告
                if e.args:
                    clsname = clspath.split('.')[-1]
                    logger.warning("Disabled %(clsname)s: %(eargs)s" % {'clsname': clsname, 'eargs': e.args[0]})

        # Log enabled middlewares
        # 记录已启用的中间件
        logger.info(f"Enabled {cls.component_name}s:\n{pprint.pformat(enabled)}")

        # Create and return a new middleware manager instance
        # 创建并返回新的中间件管理器实例
        return cls(*middlewares)

    @classmethod
    async def from_crawler(cls, crawler):
        """
        Create a middleware manager from a crawler.
        从爬虫创建中间件管理器。

        This is a convenience method that calls from_settings with the crawler's settings.
        这是一个便捷方法，使用爬虫的设置调用from_settings。

        Args:
            crawler: The crawler instance.
                    爬虫实例。

        Returns:
            AbsMiddlewareManager: A new middleware manager instance.
                                 新的中间件管理器实例。
        """
        # Create middleware manager from crawler's settings
        # 从爬虫的设置创建中间件管理器
        return await cls.from_settings(crawler.settings, crawler)

    def _add_middleware(self, mw):
        """
        Add a middleware instance to the manager.
        将中间件实例添加到管理器。

        This method registers the middleware's open_spider and close_spider methods
        if they exist. Note that close_spider methods are added to the left of the
        deque, so they are executed in reverse order.
        此方法注册中间件的open_spider和close_spider方法（如果存在）。请注意，
        close_spider方法被添加到deque的左侧，因此它们以相反的顺序执行。

        Args:
            mw: The middleware instance to add.
                要添加的中间件实例。
        """
        # Register open_spider method if it exists
        # 如果存在，则注册open_spider方法
        if hasattr(mw, 'open_spider'):
            self.methods['open_spider'].append(mw.open_spider)

        # Register close_spider method if it exists (added to the left for reverse order)
        # 如果存在，则注册close_spider方法（添加到左侧以便逆序执行）
        if hasattr(mw, 'close_spider'):
            self.methods['close_spider'].appendleft(mw.close_spider)

    async def _process_parallel(self, methodname, obj, *args):
        """
        Process middleware methods in parallel.
        并行处理中间件方法。

        This method calls the process_parallel static method with the middleware
        methods registered for the given method name.
        此方法使用为给定方法名注册的中间件方法调用process_parallel静态方法。

        Args:
            methodname: The name of the middleware method to call.
                      要调用的中间件方法的名称。
            obj: The object to pass to the middleware methods.
                传递给中间件方法的对象。
            *args: Additional arguments to pass to the middleware methods.
                  传递给中间件方法的其他参数。

        Returns:
            The result of process_parallel.
            process_parallel的结果。
        """
        # Call process_parallel with the methods registered for methodname
        # 使用为methodname注册的方法调用process_parallel
        return await self.process_parallel(self.methods[methodname], obj, *args)

    async def _process_chain(self, methodname, obj, *args):
        """
        Process middleware methods in a chain.
        链式处理中间件方法。

        This method calls the process_chain static method with the middleware
        methods registered for the given method name.
        此方法使用为给定方法名注册的中间件方法调用process_chain静态方法。

        Args:
            methodname: The name of the middleware method to call.
                      要调用的中间件方法的名称。
            obj: The object to pass to the middleware methods.
                传递给中间件方法的对象。
            *args: Additional arguments to pass to the middleware methods.
                  传递给中间件方法的其他参数。

        Returns:
            The result of process_chain.
            process_chain的结果。
        """
        # Call process_chain with the methods registered for methodname
        # 使用为methodname注册的方法调用process_chain
        return await self.process_chain(self.methods[methodname], obj, *args)

    async def _process_chain_both(self, cb_methodname, eb_methodname, obj, *args):
        """
        Process middleware methods in a chain with error handling.
        带错误处理的链式处理中间件方法。

        This method calls the process_chain_both static method with the middleware
        methods registered for the given callback and errback method names.
        此方法使用为给定回调和错误回调方法名注册的中间件方法调用process_chain_both静态方法。

        Args:
            cb_methodname: The name of the callback middleware method.
                          回调中间件方法的名称。
            eb_methodname: The name of the errback middleware method.
                          错误回调中间件方法的名称。
            obj: The object to pass to the middleware methods.
                传递给中间件方法的对象。
            *args: Additional arguments to pass to the middleware methods.
                  传递给中间件方法的其他参数。

        Returns:
            The result of process_chain_both.
            process_chain_both的结果。
        """
        # Call process_chain_both with the methods registered for cb_methodname and eb_methodname
        # 使用为cb_methodname和eb_methodname注册的方法调用process_chain_both
        return await self.process_chain_both(self.methods[cb_methodname],
                                             self.methods[eb_methodname], obj, *args)

    async def open_spider(self, spider):
        """
        Call the open_spider method of all middlewares.
        调用所有中间件的open_spider方法。

        This method is called when a spider is opened. It calls the open_spider
        method of all middlewares in parallel.
        当爬虫打开时调用此方法。它并行调用所有中间件的open_spider方法。

        Args:
            spider: The spider being opened.
                   正在打开的爬虫。
        """
        # Process open_spider methods in parallel
        # 并行处理open_spider方法
        return await self._process_parallel('open_spider', spider)

    async def close_spider(self, spider):
        """
        Call the close_spider method of all middlewares.
        调用所有中间件的close_spider方法。

        This method is called when a spider is closed. It calls the close_spider
        method of all middlewares in parallel, but in reverse order from how they
        were registered.
        当爬虫关闭时调用此方法。它并行调用所有中间件的close_spider方法，
        但顺序与它们注册的顺序相反。

        Args:
            spider: The spider being closed.
                   正在关闭的爬虫。
        """
        # Process close_spider methods in parallel (in reverse order)
        # 并行处理close_spider方法（以相反的顺序）
        return await self._process_parallel('close_spider', spider)

    @staticmethod
    async def process_parallel(callbacks, input_, *a, **kw):
        """
        Process callbacks in parallel.
        并行处理回调函数。

        This method calls all callbacks with the same input object. The callbacks
        are executed in the order they were registered, but their results are not
        passed to subsequent callbacks.
        此方法使用相同的输入对象调用所有回调函数。回调函数按照它们注册的顺序执行，
        但它们的结果不会传递给后续的回调函数。

        Args:
            callbacks: List of callback functions.
                      回调函数列表。
            input_: Input object to pass to callbacks.
                   传递给回调函数的输入对象。
            *a: Additional positional arguments.
                额外的位置参数。
            **kw: Additional keyword arguments.
                 额外的关键字参数。
        """
        # Call each callback with the same input
        # 使用相同的输入调用每个回调函数
        for callback in callbacks:
            await call_helper(callback, input_, *a, **kw)

    @staticmethod
    async def process_chain(callbacks, input_, *a, **kw):
        """
        Process callbacks in a chain.
        链式处理回调函数。

        This method calls callbacks in sequence, passing the result of each callback
        to the next one. If a callback returns None, the original input is passed
        to the next callback instead.
        此方法按顺序调用回调函数，将每个回调函数的结果传递给下一个回调函数。
        如果回调函数返回None，则原始输入将传递给下一个回调函数。

        Args:
            callbacks: List of callback functions.
                      回调函数列表。
            input_: Initial input object.
                   初始输入对象。
            *a: Additional positional arguments.
                额外的位置参数。
            **kw: Additional keyword arguments.
                 额外的关键字参数。

        Returns:
            object: The final result after all callbacks have been processed.
                   所有回调函数处理后的最终结果。
        """
        # Process each callback in sequence
        # 按顺序处理每个回调函数
        for callback in callbacks:
            # Call the callback with the current input
            # 使用当前输入调用回调函数
            input_result = await call_helper(callback, input_, *a, **kw)

            # Update input if the callback returned a non-None result
            # 如果回调函数返回非None结果，则更新输入
            if input_result is not None:
                input_ = input_result

        # Return the final result
        # 返回最终结果
        return input_

    @staticmethod
    async def process_chain_both(callbacks, errbacks, input_, *a, **kw):
        """
        Process callbacks and errbacks in a chain.
        链式处理回调函数和错误回调函数。

        This method calls callbacks in sequence, passing the result of each callback
        to the next one. If a callback raises an exception, the corresponding errback
        is called with the same input.
        此方法按顺序调用回调函数，将每个回调函数的结果传递给下一个回调函数。
        如果回调函数引发异常，则使用相同的输入调用相应的错误回调函数。

        Args:
            callbacks: List of callback functions.
                      回调函数列表。
            errbacks: List of error callback functions.
                     错误回调函数列表。
            input_: Initial input object.
                   初始输入对象。
            *a: Additional positional arguments.
                额外的位置参数。
            **kw: Additional keyword arguments.
                 额外的关键字参数。

        Returns:
            object: The final result after all callbacks have been processed.
                   所有回调函数处理后的最终结果。
        """
        # Process each callback/errback pair
        # 处理每对回调/错误回调函数
        for cb, eb in zip(callbacks, errbacks):
            try:
                # Try to call the callback
                # 尝试调用回调函数
                input_ = await call_helper(cb, input_, *a, **kw)
            except(Exception, BaseException):
                # If an exception occurs, call the errback
                # 如果发生异常，调用错误回调函数
                input_ = await call_helper(eb, input_, *a, **kw)

            # Return after the first callback/errback pair
            # 在第一对回调/错误回调函数后返回
            return input_
