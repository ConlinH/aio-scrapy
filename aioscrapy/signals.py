"""
AioScrapy Signals
AioScrapy信号

This module defines all signals that the AioScrapy framework emits during the
execution of a crawl. These signals allow developers to hook into various points
of the crawling process to add custom functionality.
此模块定义了AioScrapy框架在爬取执行过程中发出的所有信号。
这些信号允许开发人员挂钩到爬取过程的各个点，以添加自定义功能。

Signals are implemented using the PyDispatcher library and are represented as
unique objects. To connect to a signal, use the crawler.signals.connect method.
信号使用PyDispatcher库实现，并表示为唯一对象。
要连接到信号，请使用crawler.signals.connect方法。

Example:
    def handle_spider_opened(spider):
        print(f"Spider {spider.name} opened")

    crawler.signals.connect(handle_spider_opened, signal=signals.spider_opened)

These signals are documented in docs/topics/signals.rst. Please don't add new
signals here without documenting them there.
这些信号在docs/topics/signals.rst中有文档说明。
请不要在此处添加新信号，除非在那里记录它们。
"""

# Engine signals
# 引擎信号

#: Signal sent when the aioscrapy engine has started.
#: 当aioscrapy引擎启动时发送的信号。
#: Args: None
engine_started = object()

#: Signal sent when the aioscrapy engine has stopped.
#: 当aioscrapy引擎停止时发送的信号。
#: Args: None
engine_stopped = object()


# Spider signals
# 爬虫信号

#: Signal sent when a spider has been opened for crawling.
#: 当爬虫被打开进行爬取时发送的信号。
#: Args:
#:     spider (Spider): The spider that has been opened.
#:                      已被打开的爬虫。
spider_opened = object()

#: Signal sent when a spider has no more requests to process.
#: 当爬虫没有更多请求要处理时发送的信号。
#: Args:
#:     spider (Spider): The spider that has become idle.
#:                      变为空闲的爬虫。
spider_idle = object()

#: Signal sent when a spider has been closed.
#: 当爬虫被关闭时发送的信号。
#: Args:
#:     spider (Spider): The spider that has been closed.
#:                      已被关闭的爬虫。
#:     reason (str): A string describing the reason why the spider was closed.
#:                   描述爬虫被关闭原因的字符串。
spider_closed = object()

#: Signal sent when a spider callback generates an error.
#: 当爬虫回调生成错误时发送的信号。
#: Args:
#:     failure (Failure): The exception information.
#:                        异常信息。
#:     response (Response): The response that caused the error.
#:                          导致错误的响应。
#:     spider (Spider): The spider that raised the exception.
#:                      引发异常的爬虫。
spider_error = object()


# Request signals
# 请求信号

#: Signal sent when a new Request is scheduled to be downloaded.
#: 当新的Request被安排下载时发送的信号。
#: Args:
#:     request (Request): The request that reached the scheduler.
#:                        到达调度器的请求。
#:     spider (Spider): The spider that generated the request.
#:                      生成请求的爬虫。
request_scheduled = object()

#: Signal sent when a Request is dropped by the scheduler.
#: 当请求被调度器丢弃时发送的信号。
#: Args:
#:     request (Request): The request that was dropped.
#:                        被丢弃的请求。
#:     spider (Spider): The spider that generated the request.
#:                      生成请求的爬虫。
request_dropped = object()

#: Signal sent when a Request reaches the downloader.
#: 当请求到达下载器时发送的信号。
#: Args:
#:     request (Request): The request that reached the downloader.
#:                        到达下载器的请求。
#:     spider (Spider): The spider that generated the request.
#:                      生成请求的爬虫。
request_reached_downloader = object()

#: Signal sent when a Request leaves the downloader.
#: 当请求离开下载器时发送的信号。
#: Args:
#:     request (Request): The request that left the downloader.
#:                        离开下载器的请求。
#:     spider (Spider): The spider that generated the request.
#:                      生成请求的爬虫。
request_left_downloader = object()


# Response signals
# 响应信号

#: Signal sent when the downloader receives a response from the web server.
#: 当下载器从Web服务器接收到响应时发送的信号。
#: Args:
#:     response (Response): The response received.
#:                          接收到的响应。
#:     request (Request): The request that generated the response.
#:                        生成响应的请求。
#:     spider (Spider): The spider that generated the request.
#:                      生成请求的爬虫。
response_received = object()

#: Signal sent when a Response has been downloaded.
#: 当响应已被下载时发送的信号。
#: Args:
#:     response (Response): The response downloaded.
#:                          下载的响应。
#:     request (Request): The request that generated the response.
#:                        生成响应的请求。
#:     spider (Spider): The spider that generated the request.
#:                      生成请求的爬虫。
response_downloaded = object()

#: Signal sent when the HTTP headers are received for a request.
#: 当接收到请求的HTTP头时发送的信号。
#: Args:
#:     headers (dict): The HTTP headers received.
#:                     接收到的HTTP头。
#:     body_length (int): Expected size of the response body.
#:                        预期的响应正文大小。
#:     request (Request): The request that generated the response.
#:                        生成响应的请求。
#:     spider (Spider): The spider that generated the request.
#:                      生成请求的爬虫。
headers_received = object()

#: Signal sent when a chunk of response data is received.
#: 当接收到响应数据块时发送的信号。
#: Args:
#:     data (bytes): The chunk of data received.
#:                   接收到的数据块。
#:     request (Request): The request that generated the response.
#:                        生成响应的请求。
#:     spider (Spider): The spider that generated the request.
#:                      生成请求的爬虫。
bytes_received = object()


# Item signals
# 项目信号

#: Signal sent when an item has been scraped by a spider.
#: 当项目被爬虫抓取时发送的信号。
#: Args:
#:     item (Item or dict): The item scraped.
#:                          抓取的项目。
#:     response (Response): The response from which the item was scraped.
#:                          项目被抓取的响应。
#:     spider (Spider): The spider which scraped the item.
#:                      抓取项目的爬虫。
item_scraped = object()

#: Signal sent when an item is dropped by an item pipeline.
#: 当项目被项目管道丢弃时发送的信号。
#: Args:
#:     item (Item or dict): The item dropped from the pipeline.
#:                          从管道丢弃的项目。
#:     exception (Exception): The exception that caused the item to be dropped.
#:                            导致项目被丢弃的异常。
#:     spider (Spider): The spider which scraped the item.
#:                      抓取项目的爬虫。
item_dropped = object()

#: Signal sent when an item causes an error in an item pipeline.
#: 当项目在项目管道中导致错误时发送的信号。
#: Args:
#:     item (Item or dict): The item that caused the error.
#:                          导致错误的项目。
#:     exception (Exception): The exception raised.
#:                            引发的异常。
#:     spider (Spider): The spider which scraped the item.
#:                      抓取项目的爬虫。
#:     response (Response): The response from which the item was scraped.
#:                          项目被抓取的响应。
item_error = object()
