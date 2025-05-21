# API参考 | API Reference

本文档提供了AioScrapy主要类和方法的详细API参考。
This document provides a detailed API reference for the main classes and methods in AioScrapy.

## Spider API | Spider API
### Spider | Spider

```python
class Spider(object):
    """
    爬虫的基类。所有爬虫必须继承自此类。
    Base class for AioScrapy spiders. All spiders must inherit from this class.
    """
    
    name: Optional[str] = None
    proxy: Optional["aioscrapy.proxy.AbsProxy"] = None
    dupefilter: Optional["aioscrapy.dupefilters.DupeFilterBase"] = None
    custom_settings: Optional[dict] = None
    stats: Optional[StatsCollector] = None
    
    pause: bool = False
    
    def __init__(self, name=None, **kwargs):
        """
        初始化爬虫。
        Initialize the spider.

        Args:
            name: 爬虫名称。Spider name.
            **kwargs: 额外参数。Additional arguments.
        """
        pass
    
    @classmethod
    async def from_crawler(cls, crawler, *args, **kwargs):
        """
        从爬虫创建爬虫实例的类方法。
        Class method to create a spider instance from a crawler.

        Args:
            crawler: 爬虫实例。Crawler instance.
            *args: 位置参数。Positional arguments.
            **kwargs: 关键字参数。Keyword arguments.

        Returns:
            Spider: 爬虫实例。Spider instance.
        """
        pass
    
    async def start_requests(self):
        """
        返回爬虫的初始请求。
        Return the initial requests for the spider.

        Returns:
            Iterator[Request]: 请求迭代器。Iterator of requests.
        """
        pass
    
    async def parse(self, response):
        """
        处理下载的响应的默认回调方法。
        Default callback used to process downloaded responses.

        必须在子类中实现此方法。
        This method must be implemented in subclasses.

        Args:
            response: 要处理的响应。The response to process.

        Returns:
            Iterator: 包含Request和/或数据项的迭代器。Iterator containing Requests and/or items.
        """
        pass
    
    @classmethod
    def update_settings(cls, settings):
        """
        使用爬虫自定义设置更新设置。
        Update settings with spider custom settings.

        Args:
            settings: 要更新的设置。The settings to update.
        """
        pass
    
    @classmethod
    def start(cls, setting_path=None, use_windows_selector_eventLoop: bool = False):
        """
        使用此爬虫开始爬取。
        Start crawling using this spider.

        这是一个便捷方法，它创建一个CrawlerProcess，添加爬虫，并启动爬取过程。
        This is a convenience method that creates a CrawlerProcess, adds the spider,
        and starts the crawling process.

        Args:
            setting_path: 设置模块的路径。Path to settings module.
            use_windows_selector_eventLoop: 是否使用Windows选择器事件循环。Whether to use Windows selector event loop.
        """
        pass
```

## Request API | Request API
### Request | Request

```python
class Request:
    """
    表示HTTP请求的类。
    Class representing an HTTP request.
    """
    
    def __init__(
        self,
        url: str,
        callback: Optional[Callable] = None,
        method: str = 'GET',
        headers: Optional[Dict[str, str]] = None,
        body: Optional[Union[str, bytes]] = None,
        cookies: Optional[Dict[str, str]] = None,
        meta: Optional[Dict[str, Any]] = None,
        encoding: str = 'utf-8',
        priority: int = 0,
        dont_filter: bool = False,
        errback: Optional[Callable] = None,
        flags: Optional[List[str]] = None,
        cb_kwargs: Optional[Dict[str, Any]] = None
    ):
        """
        初始化请求。
        Initialize the request.

        Args:
            url: 请求的URL。The URL of the request.
            callback: 处理响应的回调函数。Callback function to process the response.
            method: HTTP方法。HTTP method.
            headers: HTTP头。HTTP headers.
            body: 请求体。Request body.
            cookies: Cookie。Cookies.
            meta: 请求元数据。Request metadata.
            encoding: 编码。Encoding.
            priority: 优先级。Priority.
            dont_filter: 是否不过滤重复请求。Whether to filter duplicate requests.
            errback: 处理错误的回调函数。Callback function to handle errors.
            flags: 标志。Flags.
            cb_kwargs: 传递给回调函数的关键字参数。Keyword arguments to pass to the callback function.
        """
        pass
    
    def copy(self):
        """
        创建请求的副本。
        Create a copy of the request.

        Returns:
            Request: 请求的副本。Copy of the request.
        """
        pass
```

### FormRequest | FormRequest

```python
class FormRequest(Request):
    """
    表示表单请求的类。
    Class representing a form request.
    """
    
    def __init__(
        self,
        url: str,
        formdata: Optional[Dict[str, str]] = None,
        **kwargs
    ):
        """
        初始化表单请求。
        Initialize the form request.

        Args:
            url: 请求的URL。The URL of the request.
            formdata: 表单数据。Form data.
            **kwargs: 传递给Request的额外参数。Additional arguments passed to Request.
        """
        pass
    
    @classmethod
    def from_response(
        cls,
        response,
        formid: Optional[str] = None,
        formname: Optional[str] = None,
        formnumber: int = 0,
        formdata: Optional[Dict[str, str]] = None,
        formxpath: Optional[str] = None,
        formcss: Optional[str] = None,
        clickdata: Optional[Dict[str, str]] = None,
        dont_click: bool = False,
        **kwargs
    ):
        """
        从响应创建表单请求。
        Create a form request from a response.

        Args:
            response: 响应对象。Response object.
            formid: 表单ID。Form ID.
            formname: 表单名称。Form name.
            formnumber: 表单编号。Form number.
            formdata: 表单数据。Form data.
            formxpath: 表单XPath。Form XPath.
            formcss: 表单CSS选择器。Form CSS selector.
            clickdata: 点击数据。Click data.
            dont_click: 是否不点击。Whether to click.
            **kwargs: 传递给FormRequest的额外参数。Additional arguments passed to FormRequest.

        Returns:
            FormRequest: 表单请求。Form request.
        """
        pass
```

## Response API | Response API
### Response | Response

```python
class Response:
    """
    表示HTTP响应的基类。
    Base class for HTTP responses.
    """
    
    def __init__(
        self,
        url: str,
        status: int = 200,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[Union[str, bytes]] = b'',
        flags: Optional[List[str]] = None,
        request: Optional[Request] = None,
        certificate: Optional[Any] = None,
        ip_address: Optional[str] = None,
        protocol: Optional[str] = None
    ):
        """
        初始化响应。
        Initialize the response.

        Args:
            url: 响应的URL。The URL of the response.
            status: HTTP状态码。HTTP status code.
            headers: HTTP头。HTTP headers.
            body: 响应体。Response body.
            flags: 标志。Flags.
            request: 生成此响应的请求。The request that generated this response.
            certificate: 证书。Certificate.
            ip_address: IP地址。IP address.
            protocol: 协议。Protocol.
        """
        pass
    
    def copy(self):
        """
        创建响应的副本。
        Create a copy of the response.

        Returns:
            Response: 响应的副本。Copy of the response.
        """
        pass
    
    def urljoin(self, url: str) -> str:
        """
        将相对URL与响应的URL连接起来。
        Join a relative URL with the response's URL.

        Args:
            url: 相对URL。Relative URL.

        Returns:
            str: 绝对URL。Absolute URL.
        """
        pass
    
    def follow(
        self,
        url: str,
        callback: Optional[Callable] = None,
        method: str = 'GET',
        headers: Optional[Dict[str, str]] = None,
        body: Optional[Union[str, bytes]] = None,
        cookies: Optional[Dict[str, str]] = None,
        meta: Optional[Dict[str, Any]] = None,
        encoding: str = 'utf-8',
        priority: int = 0,
        dont_filter: bool = False,
        errback: Optional[Callable] = None,
        flags: Optional[List[str]] = None,
        cb_kwargs: Optional[Dict[str, Any]] = None
    ) -> Request:
        """
        创建一个跟随链接的请求。
        Create a request to follow a link.

        Args:
            url: 要跟随的URL。The URL to follow.
            callback: 处理响应的回调函数。Callback function to process the response.
            method: HTTP方法。HTTP method.
            headers: HTTP头。HTTP headers.
            body: 请求体。Request body.
            cookies: Cookie。Cookies.
            meta: 请求元数据。Request metadata.
            encoding: 编码。Encoding.
            priority: 优先级。Priority.
            dont_filter: 是否不过滤重复请求。Whether to filter duplicate requests.
            errback: 处理错误的回调函数。Callback function to handle errors.
            flags: 标志。Flags.
            cb_kwargs: 传递给回调函数的关键字参数。Keyword arguments to pass to the callback function.

        Returns:
            Request: 请求对象。Request object.
        """
        pass
```

### HtmlResponse | HtmlResponse

```python
class HtmlResponse(Response):
    """
    表示HTML响应的类。
    Class representing an HTML response.
    """
    
    def __init__(self, *args, **kwargs):
        """
        初始化HTML响应。
        Initialize the HTML response.

        Args:
            *args: 位置参数。Positional arguments.
            **kwargs: 关键字参数。Keyword arguments.
        """
        pass
    
    def css(self, query: str) -> Selector:
        """
        使用CSS选择器查询响应。
        Query the response using a CSS selector.

        Args:
            query: CSS选择器。CSS selector.

        Returns:
            Selector: 选择器对象。Selector object.
        """
        pass
    
    def xpath(self, query: str) -> Selector:
        """
        使用XPath选择器查询响应。
        Query the response using an XPath selector.

        Args:
            query: XPath选择器。XPath selector.

        Returns:
            Selector: 选择器对象。Selector object.
        """
        pass
```

## 设置API | Settings API
### Settings | Settings

```python
class Settings:
    """
    表示设置的类。
    Class representing settings.
    """
    
    def __init__(self, values: Optional[Dict[str, Any]] = None):
        """
        初始化设置。
        Initialize the settings.

        Args:
            values: 初始值。Initial values.
        """
        pass
    
    def get(self, name: str, default: Any = None) -> Any:
        """
        获取设置值。
        Get a setting value.

        Args:
            name: 设置名称。Setting name.
            default: 默认值。Default value.

        Returns:
            Any: 设置值。Setting value.
        """
        pass
    
    def getbool(self, name: str, default: bool = False) -> bool:
        """
        获取布尔设置值。
        Get a boolean setting value.

        Args:
            name: 设置名称。Setting name.
            default: 默认值。Default value.

        Returns:
            bool: 布尔设置值。Boolean setting value.
        """
        pass
    
    def getint(self, name: str, default: int = 0) -> int:
        """
        获取整数设置值。
        Get an integer setting value.

        Args:
            name: 设置名称。Setting name.
            default: 默认值。Default value.

        Returns:
            int: 整数设置值。Integer setting value.
        """
        pass
    
    def getfloat(self, name: str, default: float = 0.0) -> float:
        """
        获取浮点数设置值。
        Get a float setting value.

        Args:
            name: 设置名称。Setting name.
            default: 默认值。Default value.

        Returns:
            float: 浮点数设置值。Float setting value.
        """
        pass
    
    def getlist(self, name: str, default: Optional[List[Any]] = None) -> List[Any]:
        """
        获取列表设置值。
        Get a list setting value.

        Args:
            name: 设置名称。Setting name.
            default: 默认值。Default value.

        Returns:
            List[Any]: 列表设置值。List setting value.
        """
        pass
    
    def getdict(self, name: str, default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        获取字典设置值。
        Get a dictionary setting value.

        Args:
            name: 设置名称。Setting name.
            default: 默认值。Default value.

        Returns:
            Dict[str, Any]: 字典设置值。Dictionary setting value.
        """
        pass
    
    def set(self, name: str, value: Any, priority: str = 'project') -> None:
        """
        设置设置值。
        Set a setting value.

        Args:
            name: 设置名称。Setting name.
            value: 设置值。Setting value.
            priority: 优先级。Priority.
        """
        pass
    
    def setmodule(self, module: Union[str, ModuleType], priority: str = 'project') -> None:
        """
        从模块设置设置值。
        Set settings values from a module.

        Args:
            module: 模块或模块路径。Module or module path.
            priority: 优先级。Priority.
        """
        pass
    
    def setdict(self, values: Dict[str, Any], priority: str = 'project') -> None:
        """
        从字典设置设置值。
        Set settings values from a dictionary.

        Args:
            values: 设置值字典。Dictionary of setting values.
            priority: 优先级。Priority.
        """
        pass
```

## 日志API | Logging API
### Logger | Logger

使用方法：
Usage:

```python
from aioscrapy import logger

logger.debug('Debug message')
logger.info('Info message')
logger.warning('Warning message')
logger.error('Error message')
logger.critical('Critical message')
```
