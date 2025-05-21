# 下载器 | Downloaders

下载器是AioScrapy的核心组件之一，负责从互联网获取网页和其他资源。AioScrapy支持多种下载处理程序，可以根据需要选择不同的HTTP客户端。</br>
Downloaders are one of the core components of AioScrapy, responsible for fetching web pages and other resources from the internet. AioScrapy supports multiple download handlers, allowing you to choose different HTTP clients as needed.

## 下载器架构 | Downloader Architecture

AioScrapy的下载器系统由以下主要组件组成：</br>
The AioScrapy downloader system consists of the following main components:

1. **Downloader**：主下载器类，管理请求队列和并发
2. **DownloadHandlerManager**：管理不同URL方案的下载处理程序
3. **BaseDownloadHandler**：下载处理程序的基类
4. **具体下载处理程序**：如AioHttpDownloadHandler、HttpxDownloadHandler等

</br>

1. **Downloader**: Main downloader class, manages request queues and concurrency
2. **DownloadHandlerManager**: Manages download handlers for different URL schemes
3. **BaseDownloadHandler**: Base class for download handlers
4. **Specific Download Handlers**: Such as AioHttpDownloadHandler, HttpxDownloadHandler, etc.

## 支持的下载处理程序 | Supported Download Handlers

AioScrapy支持多种下载处理程序，每种都有其特点和适用场景：</br>
AioScrapy supports multiple download handlers, each with its own characteristics and use cases:

### aiohttp（默认） | aiohttp (Default)

基于aiohttp库的异步HTTP客户端，是AioScrapy的默认下载处理程序。</br>
An asynchronous HTTP client based on the aiohttp library, which is the default download handler for AioScrapy.

**特点 | Features**：
- 完全异步 | Fully asynchronous
- 高性能 | High performance
- 支持HTTP/1.1 | HTTP/1.1 support
- 支持代理 | Proxy support
- 支持Cookie | Cookie support

**配置示例 | Configuration Example**：
```python
# 在settings.py中设置 | Set in settings.py
DOWNLOAD_HANDLERS_TYPE = "aiohttp"  # 默认值，可以省略 | Default value, can be omitted

# 或者直接指定处理程序 | Or directly specify handlers
# DOWNLOAD_HANDLERS = {
#     'http': 'aioscrapy.core.downloader.handlers.aiohttp.AioHttpDownloadHandler',
#     'https': 'aioscrapy.core.downloader.handlers.aiohttp.AioHttpDownloadHandler',
# }

# aiohttp特定设置 | aiohttp-specific settings
AIOHTTP_ARGS = {
    'timeout': 30,
    'connector': {'limit': 100, 'force_close': True}
}
```

### httpx

基于httpx库的现代HTTP客户端，支持HTTP/2。</br>
A modern HTTP client based on the httpx library, with HTTP/2 support.

**特点 | Features**：
- 支持HTTP/1.1和HTTP/2 | HTTP/1.1 and HTTP/2 support
- 异步API | Asynchronous API
- 现代化的接口 | Modern interface
- 支持代理 | Proxy support
- 支持Cookie | Cookie support


**配置示例 | Configuration Example**：
```python
# 安装httpx | Install httpx
# pip install httpx

# 在settings.py中设置 | Set in settings.py
DOWNLOAD_HANDLERS_TYPE = "httpx"

# 或者直接指定处理程序 | Or directly specify handlers
# DOWNLOAD_HANDLERS = {
#     'http': 'aioscrapy.core.downloader.handlers.httpx.HttpxDownloadHandler',
#     'https': 'aioscrapy.core.downloader.handlers.httpx.HttpxDownloadHandler',
# }

# httpx特定设置 | httpx-specific settings
HTTPX_ARGS = {
    'timeout': 30,
    'limits': {'max_connections': 100}
}
```

### pyhttpx

基于pyhttpx库的HTTP客户端，支持HTTP/2和TLS指纹修改。</br>
An HTTP client based on the pyhttpx library, with HTTP/2 and TLS fingerprint modification support.

**特点 | Features**：
- 支持HTTP/2 | HTTP/2 support
- 支持TLS指纹修改 | TLS fingerprint modification support
- 支持代理 | Proxy support
- 支持Cookie | Cookie support


**配置示例 | Configuration Example**：
```python
# 安装pyhttpx | Install pyhttpx
# pip install pyhttpx

# 在settings.py中设置 | Set in settings.py
DOWNLOAD_HANDLERS_TYPE = "pyhttpx"

# 或者直接指定处理程序 | Or directly specify handlers
# DOWNLOAD_HANDLERS = {
#     'http': 'aioscrapy.core.downloader.handlers.pyhttpx.PyhttpxDownloadHandler',
#     'https': 'aioscrapy.core.downloader.handlers.pyhttpx.PyhttpxDownloadHandler',
# }

# pyhttpx特定设置 | pyhttpx-specific settings
PYHTTPX_ARGS = {
    'timeout': 30,
    'http2': True
}
```

### requests

基于requests库的同步HTTP客户端，在线程池中运行。</br>
A synchronous HTTP client based on the requests library, running in a thread pool.

**特点 | Features**：
- 简单易用 | Simple and easy to use
- 广泛支持 | Widely supported
- 在线程池中运行 | Runs in a thread pool
- 支持代理 | Proxy support
- 支持Cookie | Cookie support

**配置示例 | Configuration Example**：
```python
# 安装requests | Install requests
# pip install requests

# 在settings.py中设置 | Set in settings.py
DOWNLOAD_HANDLERS_TYPE = "requests"

# 或者直接指定处理程序 | Or directly specify handlers
# DOWNLOAD_HANDLERS = {
#     'http': 'aioscrapy.core.downloader.handlers.requests.RequestsDownloadHandler',
#     'https': 'aioscrapy.core.downloader.handlers.requests.RequestsDownloadHandler',
# }

```

### curl_cffi

基于curl_cffi的HTTP客户端，支持自定义TLS指纹。</br>
An HTTP client based on curl_cffi, with custom TLS fingerprint support.

**特点 | Features**：
- 支持自定义TLS指纹 | Custom TLS fingerprint support
- 基于libcurl | Based on libcurl
- 支持HTTP/2 | HTTP/2 support
- 支持代理 | Proxy support
- 支持Cookie | Cookie support

**配置示例 | Configuration Example**：
```python
# 安装curl_cffi | Install curl_cffi
# pip install curl_cffi

# 在settings.py中设置 | Set in settings.py
DOWNLOAD_HANDLERS_TYPE = "curl_cffi"

# 或者直接指定处理程序 | Or directly specify handlers
# DOWNLOAD_HANDLERS={
#     'http': 'aioscrapy.core.downloader.handlers.curl_cffi.CurlCffiDownloadHandler',
#     'https': 'aioscrapy.core.downloader.handlers.curl_cffi.CurlCffiDownloadHandler',
# }

# curl_cffi特定设置 | curl_cffi-specific settings
CURL_CFFI_ARGS = {
    'timeout': 30,
    'impersonate': 'chrome131'
}
```

### playwright

基于Playwright的浏览器自动化工具，支持JavaScript渲染。</br>
A browser automation tool based on Playwright, with JavaScript rendering support.

**特点 | Features**：
- 支持JavaScript渲染 | JavaScript rendering support
- 完整的浏览器环境 | Full browser environment
- 支持多种浏览器（Chromium、Firefox、WebKit） | Support for multiple browsers (Chromium, Firefox, WebKit)
- 支持截图和PDF生成 | Screenshot and PDF generation support
- 支持代理 | Proxy support

**配置示例 | Configuration Example**：
```python
# 安装playwright | Install playwright
# pip install playwright | python -m playwright install

# 在settings.py中设置 | Set in settings.py
DOWNLOAD_HANDLERS_TYPE = "playwright"

# 或者直接指定处理程序 | Or directly specify handlers
# DOWNLOAD_HANDLERS={
#     'http': 'aioscrapy.core.downloader.handlers.webdriver.playwright.PlaywrightDownloadHandler',
#     'https': 'aioscrapy.core.downloader.handlers.webdriver.playwright.PlaywrightDownloadHandler',
# }

# playwright特定设置 | playwright-specific settings
PLAYWRIGHT_ARGS = {
    'use_pool': True,
    'max_uses': None,
    'driver_type': 'chromium',  # 'chromium', 'firefox', 或 'webkit' | 'chromium', 'firefox', or 'webkit'
    'wait_until': "networkidle",
    'window_size': (1024, 800),
    # 'proxy': 'http://user:pwd@127.0.0.1:7890',
    # 'browser_args': dict(
    #     executable_path=None, channel=None, args=None, ignore_default_args=None, handle_sigint=None,
    #     handle_sigterm=None, handle_sighup=None, timeout=None, env=None, headless=False, devtools=None,
    #     downloads_path=None, slow_mo=None, traces_dir=None, chromium_sandbox=None,
    #     firefox_user_prefs=None,
    # ),
    # 'context_args': dict(
    #     no_viewport=None, ignore_https_errors=None, java_script_enabled=None,
    #     bypass_csp=None, user_agent=None, locale=None, timezone_id=None, geolocation=None, permissions=None,
    #     extra_http_headers=None, offline=None, http_credentials=None, device_scale_factor=None,
    #     is_mobile=None, has_touch=None, color_scheme=None, reduced_motion=None, forced_colors=None,
    #     accept_downloads=None, default_browser_type=None, record_har_path=None,
    #     record_har_omit_content=None, record_video_dir=None, record_video_size=None, storage_state=None,
    #     base_url=None, strict_selectors=None, service_workers=None, record_har_url_filter=None,
    #     record_har_mode=None, record_har_content=None,
    # ),
}
```

### DrissionPage

基于DrissionPage的浏览器自动化工具，支持JavaScript渲染。</br>
A browser automation tool based on DrissionPage, with JavaScript rendering support.

**特点 | Features**：
- 支持JavaScript渲染 | JavaScript rendering support
- 完整的浏览器环境 | Full browser environment
- 支持截图和PDF生成 | Screenshot and PDF generation support
- 支持代理 | Proxy support

**配置示例 | Configuration Example**：
```python
# 安装DrissionPage | Install DrissionPage
# pip install DrissionPage

# 在settings.py中设置 | Set in settings.py
DOWNLOAD_HANDLERS_TYPE = "dp"

# 或者直接指定处理程序 | Or directly specify handlers
# DOWNLOAD_HANDLERS={
#     'http': 'aioscrapy.core.downloader.handlers.webdriver.drissionpage.DrissionPageDownloadHandler',
#     'https': 'aioscrapy.core.downloader.handlers.webdriver.drissionpage.DrissionPageDownloadHandler',
# },

# playwright特定设置 | playwright-specific settings
DP_ARGS = {
    'use_pool': True,
    'max_uses': None,
    'headless': False,
     arguments=['--no-sandbox', ('--window-size', '1024,800')]
    # 'proxy': 'http://user:pwd@127.0.0.1:7890',
}
```


## 自定义下载处理程序 | Custom Download Handlers

您可以创建自己的下载处理程序，只需继承`BaseDownloadHandler`类并实现必要的方法：</br>
You can create your own download handler by inheriting from the `BaseDownloadHandler` class and implementing the necessary methods:

```python
from aioscrapy.core.downloader.handlers import BaseDownloadHandler
from aioscrapy import Request, Spider
from aioscrapy.http import HtmlResponse

class MyCustomDownloadHandler(BaseDownloadHandler):

    # 初始化您的HTTP客户端 | Initialize your HTTP client
    def __init__(self, settings):
        self.settings = settings

    # 实现下载逻辑 | Implement download logic
    async def download_request(self, request: Request, spider: Spider) -> HtmlResponse:
        pass
        # 返回HtmlResponse对象 | Return an HtmlResponse object

    # 关闭资源 | Close resources
    async def close(self):
        pass
```

然后在设置中注册您的处理程序：</br>
Then register your handler in the settings:

```python
DOWNLOAD_HANDLERS = {
    'http': 'myproject.handlers.MyCustomDownloadHandler',
    'https': 'myproject.handlers.MyCustomDownloadHandler',
}
```

## 下载器中间件 | Downloader Middleware

下载器中间件允许您在请求被发送到下载处理程序之前和响应被返回给爬虫之后处理它们。详细信息请参见[中间件](middlewares.md)文档。</br>
Downloader middleware allows you to process requests before they are sent to the download handler and responses after they are returned to the spider. See the [Middlewares](middlewares.md) documentation for details.
