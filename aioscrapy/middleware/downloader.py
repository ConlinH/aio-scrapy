"""
Downloader Middleware Manager Module
下载器中间件管理器模块

This module provides the DownloaderMiddlewareManager class, which manages the execution
of downloader middleware components. Downloader middlewares process requests before they
are sent to the downloader and responses before they are sent to the spider.
此模块提供了DownloaderMiddlewareManager类，用于管理下载器中间件组件的执行。
下载器中间件在请求发送到下载器之前处理请求，在响应发送到爬虫之前处理响应。

Downloader middlewares can modify requests and responses, return alternative responses,
or handle exceptions that occur during the download process.
下载器中间件可以修改请求和响应，返回替代响应，或处理下载过程中发生的异常。
"""
from aioscrapy.exceptions import _InvalidOutput
from aioscrapy.http import Request, Response
from aioscrapy.middleware.absmanager import AbsMiddlewareManager
from aioscrapy.utils.conf import build_component_list
from aioscrapy.utils.tools import call_helper


class DownloaderMiddlewareManager(AbsMiddlewareManager):
    """
    Manager for downloader middleware components.
    下载器中间件组件的管理器。

    This class manages the execution of downloader middleware components, which process
    requests before they are sent to the downloader and responses before they are sent
    to the spider. It inherits from AbsMiddlewareManager and implements the specific
    behavior for downloader middlewares.
    此类管理下载器中间件组件的执行，这些组件在请求发送到下载器之前处理请求，
    在响应发送到爬虫之前处理响应。它继承自AbsMiddlewareManager，并实现了
    下载器中间件的特定行为。
    """

    # Name of the middleware component
    # 中间件组件的名称
    component_name = 'downloader middleware'

    @classmethod
    def _get_mwlist_from_settings(cls, settings):
        """
        Get the list of middleware classes from settings.
        从设置中获取中间件类列表。

        This method implements the abstract method from AbsMiddlewareManager.
        It retrieves the list of downloader middleware classes from the
        DOWNLOADER_MIDDLEWARES setting.
        此方法实现了AbsMiddlewareManager中的抽象方法。它从DOWNLOADER_MIDDLEWARES
        设置中检索下载器中间件类列表。

        Args:
            settings: The settings object.
                     设置对象。

        Returns:
            list: A list of middleware class paths.
                 中间件类路径列表。
        """
        # Build component list from DOWNLOADER_MIDDLEWARES setting
        # 从DOWNLOADER_MIDDLEWARES设置构建组件列表
        return build_component_list(
            settings.getwithbase('DOWNLOADER_MIDDLEWARES'))

    def _add_middleware(self, mw):
        """
        Add a middleware instance to the manager.
        将中间件实例添加到管理器。

        This method overrides the method from AbsMiddlewareManager to register
        the specific methods of downloader middlewares: process_request,
        process_response, and process_exception.
        此方法覆盖了AbsMiddlewareManager中的方法，以注册下载器中间件的特定方法：
        process_request、process_response和process_exception。

        Note that process_request methods are called in the order they are registered,
        while process_response and process_exception methods are called in reverse order.
        请注意，process_request方法按照它们注册的顺序调用，而process_response
        和process_exception方法按照相反的顺序调用。

        Args:
            mw: The middleware instance to add.
                要添加的中间件实例。
        """
        # Register process_request method if it exists
        # 如果存在，则注册process_request方法
        if hasattr(mw, 'process_request'):
            self.methods['process_request'].append(mw.process_request)

        # Register process_response method if it exists (added to the left for reverse order)
        # 如果存在，则注册process_response方法（添加到左侧以便逆序执行）
        if hasattr(mw, 'process_response'):
            self.methods['process_response'].appendleft(mw.process_response)

        # Register process_exception method if it exists (added to the left for reverse order)
        # 如果存在，则注册process_exception方法（添加到左侧以便逆序执行）
        if hasattr(mw, 'process_exception'):
            self.methods['process_exception'].appendleft(mw.process_exception)

    def iter_mw_method(self, spider, process_type: str):
        """
        Iterate over middleware methods of a specific type.
        迭代特定类型的中间件方法。

        This method yields all middleware methods of the specified type, followed
        by the spider's method of the same type if it exists.
        此方法产生指定类型的所有中间件方法，如果存在，则后跟爬虫的同类型方法。

        Args:
            spider: The spider instance.
                   爬虫实例。
            process_type: The type of middleware method to iterate over.
                         要迭代的中间件方法类型。

        Yields:
            callable: Middleware methods of the specified type.
                     指定类型的中间件方法。
        """
        # Get the spider's method of the specified type if it exists
        # 如果存在，则获取爬虫的指定类型方法
        spider_method = getattr(spider, process_type, None)

        # Yield all middleware methods of the specified type
        # 产生指定类型的所有中间件方法
        for method in self.methods[process_type]:
            yield method

        # Yield the spider's method if it exists
        # 如果存在，则产生爬虫的方法
        if spider_method:
            yield spider_method

    async def process_request(self, spider, request):
        """
        Process a request through all registered process_request methods.
        通过所有已注册的process_request方法处理请求。

        This method calls each middleware's process_request method in the order
        they were registered. If any middleware returns a Response or Request,
        the process stops and that object is returned.
        此方法按照它们注册的顺序调用每个中间件的process_request方法。如果任何
        中间件返回Response或Request，则过程停止并返回该对象。

        Args:
            spider: The spider instance.
                   爬虫实例。
            request: The request to process.
                    要处理的请求。

        Returns:
            None, Response, or Request: The result of processing the request.
                                       处理请求的结果。

        Raises:
            _InvalidOutput: If a middleware returns a value that is not None, Response, or Request.
                           如果中间件返回的值不是None、Response或Request。
        """
        # Iterate over all process_request methods
        # 迭代所有process_request方法
        for method in self.iter_mw_method(spider, 'process_request'):
            # Call the method with the request
            # 使用请求调用方法
            response = await call_helper(method, request=request, spider=spider)

            # Validate the return value
            # 验证返回值
            if response is not None and not isinstance(response, (Response, Request)):
                raise _InvalidOutput(
                    "Middleware %s.process_request must return None, Response or Request, got %s"
                    % (method.__self__.__class__.__name__, response.__class__.__name__)
                )

            # If a non-None value was returned, return it and stop processing
            # 如果返回了非None值，则返回它并停止处理
            if response:
                return response

    async def process_response(self, spider, request, response):
        """
        Process a response through all registered process_response methods.
        通过所有已注册的process_response方法处理响应。

        This method calls each middleware's process_response method in reverse
        order from how they were registered. If any middleware returns a Request,
        the process stops and that Request is returned.
        此方法按照与它们注册的相反的顺序调用每个中间件的process_response方法。
        如果任何中间件返回Request，则过程停止并返回该Request。

        Args:
            spider: The spider instance.
                   爬虫实例。
            request: The request that generated the response.
                    生成响应的请求。
            response: The response to process.
                     要处理的响应。

        Returns:
            Response or Request: The result of processing the response.
                                处理响应的结果。

        Raises:
            TypeError: If response is None.
                      如果响应为None。
            _InvalidOutput: If a middleware returns a value that is not Response or Request.
                           如果中间件返回的值不是Response或Request。
        """
        # Validate the response
        # 验证响应
        if response is None:
            raise TypeError("Received None in process_response")
        elif isinstance(response, Request):
            return response

        # Iterate over all process_response methods
        # 迭代所有process_response方法
        for method in self.iter_mw_method(spider, 'process_response'):
            # Call the method with the request and response
            # 使用请求和响应调用方法
            response = await call_helper(method, request=request, response=response, spider=spider)

            # Validate the return value
            # 验证返回值
            if not isinstance(response, (Response, Request)):
                raise _InvalidOutput(
                    "Middleware %s.process_response must return Response or Request, got %s"
                    % (method.__self__.__class__.__name__, type(response))
                )

            # If a Request was returned, return it and stop processing
            # 如果返回了Request，则返回它并停止处理
            if isinstance(response, Request):
                return response

        # Return the final response
        # 返回最终响应
        return response

    async def process_exception(self, spider, request, exception):
        """
        Process an exception through all registered process_exception methods.
        通过所有已注册的process_exception方法处理异常。

        This method calls each middleware's process_exception method in reverse
        order from how they were registered. If any middleware returns a Response
        or Request, the process stops and that object is returned.
        此方法按照与它们注册的相反的顺序调用每个中间件的process_exception方法。
        如果任何中间件返回Response或Request，则过程停止并返回该对象。

        Args:
            spider: The spider instance.
                   爬虫实例。
            request: The request that caused the exception.
                    导致异常的请求。
            exception: The exception that occurred.
                      发生的异常。

        Returns:
            Exception, Response, or Request: The result of processing the exception.
                                           处理异常的结果。

        Raises:
            _InvalidOutput: If a middleware returns a value that is not None, Response, or Request.
                           如果中间件返回的值不是None、Response或Request。
        """
        # Iterate over all process_exception methods
        # 迭代所有process_exception方法
        for method in self.iter_mw_method(spider, 'process_exception'):
            # Call the method with the request and exception
            # 使用请求和异常调用方法
            response = await call_helper(method, request=request, exception=exception, spider=spider)

            # Validate the return value
            # 验证返回值
            if response is not None and not isinstance(response, (Response, Request)):
                raise _InvalidOutput(
                    "Middleware %s.process_exception must return None, Response or Request, got %s"
                    % (method.__self__.__class__.__name__, type(response))
                )

            # If a non-None value was returned, return it and stop processing
            # 如果返回了非None值，则返回它并停止处理
            if response:
                return response

        # If no middleware handled the exception, return it
        # 如果没有中间件处理异常，则返回它
        return exception
