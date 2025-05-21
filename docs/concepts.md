# 核心概念 | Core Concepts

本文档介绍了AioScrapy的核心概念和架构，帮助您理解框架的工作原理。</br>
This document introduces the core concepts and architecture of AioScrapy, helping you understand how the framework works.

## 架构概述 | Architecture Overview

AioScrapy是一个基于异步IO的网络爬虫框架，它的架构由以下主要组件组成：</br>
AioScrapy is an asynchronous IO-based web crawling framework with an architecture composed of the following main components:

1. **引擎（Engine）**：协调所有组件之间的数据流
2. **调度器（Scheduler）**：接收引擎发送的请求，并在引擎请求时返回它们
3. **下载器（Downloader）**：获取网页并将它们返回给引擎
4. **爬虫（Spiders）**：处理下载的响应并提取数据和新的请求
5. **项目管道（Item Pipelines）**：处理爬虫提取的数据
6. **中间件（Middlewares）**：处理请求和响应的钩子

</br>

1. **Engine**: Coordinates the data flow between all components
2. **Scheduler**: Receives requests from the engine and returns them when requested
3. **Downloader**: Fetches web pages and returns them to the engine
4. **Spiders**: Process downloaded responses and extract data and new requests
5. **Item Pipelines**: Process items extracted by spiders
6. **Middlewares**: Hooks for processing requests and responses

## 数据流 | Data Flow

AioScrapy中的数据流如下：
The data flow in AioScrapy is as follows:

1. 引擎从爬虫获取初始请求
2. 引擎将请求发送给调度器，并请求下一个要爬取的请求
3. 调度器返回下一个请求给引擎
4. 引擎通过下载器中间件将请求发送到下载器
5. 下载完成后，下载器生成一个响应，并通过下载器中间件将其发送到引擎
6. 引擎接收到响应，并通过爬虫中间件将其发送到爬虫进行处理
7. 爬虫处理响应，并将提取的数据项和新的请求返回给引擎
8. 引擎将提取的数据项发送给项目管道，并将新的请求发送给调度器
9. 重复步骤2-8，直到没有更多请求

</br>

1. The engine gets the initial requests from the spider
2. The engine sends the requests to the scheduler and asks for the next request to crawl
3. The scheduler returns the next request to the engine
4. The engine sends the request to the downloader through the downloader middleware
5. Once the page is downloaded, the downloader generates a response and sends it to the engine through the downloader middleware
6. The engine receives the response and sends it to the spider for processing through the spider middleware
7. The spider processes the response and returns extracted items and new requests to the engine
8. The engine sends extracted items to item pipelines and new requests to the scheduler
9. Steps 2-8 repeat until there are no more requests

## 异步架构 | Asynchronous Architecture

AioScrapy使用Python的asyncio库实现异步操作，这使得它能够高效地处理大量并发请求。</br>
AioScrapy uses Python's asyncio library to implement asynchronous operations, allowing it to efficiently handle a large number of concurrent requests.

主要的异步组件包括：</br>
The main asynchronous components include:

- **异步下载器**：使用异步HTTP客户端（如aiohttp、httpx）执行请求
- **异步管道**：使用异步数据库客户端（如motor、aiomysql）存储数据
- **异步中间件**：使用异步方法处理请求和响应
- **异步爬虫**：使用异步方法解析响应和生成请求

</br>

- **Asynchronous Downloader**: Uses asynchronous HTTP clients (like aiohttp, httpx) to perform requests
- **Asynchronous Pipelines**: Uses asynchronous database clients (like motor, aiomysql) to store data
- **Asynchronous Middlewares**: Uses asynchronous methods to process requests and responses
- **Asynchronous Spiders**: Uses asynchronous methods to parse responses and generate requests

## 爬虫 | Spiders

爬虫是AioScrapy的核心组件，它们定义了如何爬取网站和提取数据。</br>
Spiders are the core components of AioScrapy, defining how to crawl websites and extract data.

每个爬虫都必须继承自`Spider`基类，并实现以下方法：</br>
Each spider must inherit from the `Spider` base class and implement the following methods:

- **parse**：处理下载的响应并提取数据和新的请求 | Process downloaded responses and extract data and new requests
- **start_requests**（可选 | optional）：生成初始请求 | Generate initial requests

详细信息请参见[爬虫指南](spiders.md)。</br>
See the [Spider Guide](spiders.md) for detailed information.

## 请求和响应 | Requests and Responses

AioScrapy中的请求和响应是数据流的基本单位。</br>
Requests and responses are the basic units of data flow in AioScrapy.

### 请求 | Requests

请求由以下主要属性组成：</br>
Requests consist of the following main attributes:

- **url**：要请求的URL | The URL to request
- **method**：HTTP方法（GET、POST等）| The HTTP method (GET, POST, etc.)
- **headers**：HTTP头 | HTTP headers
- **body**：请求体 | Request body
- **meta**：请求元数据，可用于在请求和回调之间传递数据 | Request metadata, can be used to pass data between requests and callbacks
- **callback**：处理响应的回调函数 | The callback function to process the response
- **errback**：处理请求错误的回调函数 | The callback function to handle request errors

### 响应 | Responses

响应由以下主要属性组成：</br>
Responses consist of the following main attributes:

- **url**：响应的URL | The URL of the response
- **status**：HTTP状态码 | The HTTP status code
- **headers**：HTTP头 | HTTP headers
- **body**：响应体 | Response body
- **request**：生成此响应的请求 | The request that generated this response
- **meta**：响应元数据，继承自请求的meta | Response metadata, inherited from the request's meta

## 选择器 | Selectors

AioScrapy提供了强大的选择器API，用于从HTML和XML响应中提取数据。</br>
AioScrapy provides a powerful selector API for extracting data from HTML and XML responses.

选择器基于lxml库，支持CSS和XPath表达式：</br>
Selectors are based on the lxml library and support CSS and XPath expressions:

```python
# 使用CSS选择器 | Using CSS selectors
title = response.css('title::text').get()
links = response.css('a::attr(href)').getall()

# 使用XPath选择器 | Using XPath selectors
title = response.xpath('//title/text()').get()
links = response.xpath('//a/@href').getall()
```

## 中间件 | Middlewares

中间件是处理请求和响应的钩子，分为两种类型：</br>
Middlewares are hooks for processing requests and responses, divided into two types:

### 下载器中间件 | Downloader Middleware

下载器中间件位于引擎和下载器之间，可以处理请求在发送到下载器之前和响应在返回到引擎之后的过程。</br>
Downloader middleware sits between the engine and the downloader, processing requests before they are sent to the downloader and responses after they are returned to the engine.

详细信息请参见[中间件](middlewares.md)。</br>
See [Middlewares](middlewares.md) for detailed information.

### 爬虫中间件 | Spider Middleware

爬虫中间件位于引擎和爬虫之间，可以处理爬虫生成的请求和下载器返回的响应。</br>
Spider middleware sits between the engine and the spider, processing requests generated by the spider and responses returned by the downloader.

详细信息请参见[中间件](middlewares.md)。</br>
See [Middlewares](middlewares.md) for detailed information.

## 管道 | Pipelines

管道是处理爬虫提取的数据的组件，它们可以执行以下操作：
Pipelines are components that process data extracted by spiders, they can perform the following operations:

- 清洗数据 | Clean data
- 验证数据 | Validate data
- 检查重复 | Check for duplicates
- 存储数据到数据库 | Store data in a database

详细信息请参见[管道](pipelines.md)。</br>
See [Pipelines](pipelines.md) for detailed information.

## 下载器 | Downloaders

下载器负责从互联网获取网页和其他资源。AioScrapy支持多种下载处理程序，可以根据需要选择不同的HTTP客户端。</br>
Downloaders are responsible for fetching web pages and other resources from the internet. AioScrapy supports multiple download handlers, allowing you to choose different HTTP clients as needed.

详细信息请参见[下载器](downloaders.md)。</br>
See [Downloaders](downloaders.md) for detailed information.

## 信号 | Signals

AioScrapy使用信号系统允许组件在特定事件发生时触发操作。</br>
AioScrapy uses a signal system to allow components to trigger actions when specific events occur.

常用信号包括：
Common signals include:

- **spider_opened**：爬虫开始时触发 | Triggered when a spider starts
- **spider_closed**：爬虫关闭时触发 | Triggered when a spider closes
- **item_scraped**：项目被爬取时触发 | Triggered when an item is scraped
- **request_scheduled**：请求被调度时触发 | Triggered when a request is scheduled
- **response_received**：响应被接收时触发 | Triggered when a response is received

## 设置 | Settings

AioScrapy提供了丰富的配置选项，允许您自定义爬虫的行为。</br>
AioScrapy provides a rich set of configuration options that allow you to customize the behavior of your spiders.

详细信息请参见[配置参考](settings.md)。</br>
See [Settings Reference](settings.md) for detailed information.
