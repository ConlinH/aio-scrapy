"""
Playwright response implementation for aioscrapy.
aioscrapy的WebDriverResponse响应实现。

This module provides the PlaywrightResponse class, which is a specialized TextResponse
for handling responses from Playwright browser automation. It adds support for
browser driver management and response caching.
此模块提供了WebDriverResponse类，这是一个专门用于处理来自Playwright/DrissionPage等浏览器自动化的响应的TextResponse。
它添加了对浏览器驱动程序管理和响应缓存的支持。
"""

from typing import Optional, Any

from aioscrapy.http.response.text import TextResponse


class WebDriverResponse(TextResponse):
    """
    A Response subclass for handling Playwright browser automation responses.
    用于处理Playwright浏览器自动化响应的Response子类。

    This class extends TextResponse to handle responses from Playwright browser automation.
    It adds support for:
    此类扩展了TextResponse以处理来自Playwright浏览器自动化的响应。
    它添加了对以下内容的支持：

    - Browser driver management
      浏览器驱动程序管理
    - Response caching
      响应缓存
    - Text content override
      文本内容覆盖
    - Intercepted request data
      拦截的请求数据
    """

    def __init__(
            self,
            *args,
            text: str = '',
            cache_response: Optional[dict] = None,
            driver: Optional["WebDriverBase"] = None,
            driver_pool: Optional["WebDriverPool"] = None,
            intercept_request: Optional[dict] = None,
            **kwargs
    ):
        """
        Initialize a PlaywrightResponse.
        初始化PlaywrightResponse。

        Args:
            *args: Positional arguments passed to the TextResponse constructor.
                  传递给TextResponse构造函数的位置参数。
            text: The text content of the response, which can override the body's decoded text.
                 响应的文本内容，可以覆盖正文的解码文本。
            cache_response: A dictionary of cached response data.
                          缓存的响应数据字典。
            driver: The Playwright driver instance used for this response.
                   用于此响应的Playwright驱动程序实例。
            driver_pool: The WebDriverPool that manages the driver.
                        管理驱动程序的WebDriverPool。
            intercept_request: A dictionary of intercepted request data.
                             拦截的请求数据字典。
            **kwargs: Keyword arguments passed to the TextResponse constructor.
                     传递给TextResponse构造函数的关键字参数。
        """
        # Store Playwright-specific attributes
        # 存储Playwright特定的属性
        self.driver = driver
        self.driver_pool = driver_pool
        self._text = text
        self.cache_response = cache_response or {}
        self.intercept_request = intercept_request

        # Initialize the base TextResponse
        # 初始化基本TextResponse
        super().__init__(*args, **kwargs)

    async def release(self):
        """
        Release the Playwright driver back to the pool.
        将Playwright驱动程序释放回池中。

        This method releases the driver instance back to the WebDriverPool
        if both the driver and pool are available.
        如果驱动程序和池都可用，此方法将驱动程序实例释放回WebDriverPool。

        Returns:
            None
        """
        self.driver_pool and self.driver and await self.driver_pool.release(self.driver)

    @property
    def text(self):
        """
        Get the response text content.
        获取响应文本内容。

        This property overrides the base TextResponse.text property to return
        the explicitly set text content if available, otherwise falls back to
        the decoded body text from the parent class.
        此属性重写了基本TextResponse.text属性，如果可用，则返回明确设置的文本内容，
        否则回退到父类的解码正文文本。

        Returns:
            str: The response text content.
                响应文本内容。
        """
        return self._text or super().text

    @text.setter
    def text(self, text):
        """
        Set the response text content.
        设置响应文本内容。

        This setter allows explicitly setting the text content of the response,
        which will override the decoded body text.
        此设置器允许明确设置响应的文本内容，这将覆盖解码的正文文本。

        Args:
            text: The text content to set.
                 要设置的文本内容。
        """
        self._text = text

    def get_response(self, key) -> Any:
        """
        Get a value from the cached response data.
        从缓存的响应数据中获取值。

        This method retrieves a value from the cache_response dictionary
        using the provided key.
        此方法使用提供的键从cache_response字典中检索值。

        Args:
            key: The key to look up in the cached response data.
                 在缓存的响应数据中查找的键。

        Returns:
            Any: The value associated with the key, or None if the key is not found.
                与键关联的值，如果未找到键，则为None。
        """
        return self.cache_response.get(key)
