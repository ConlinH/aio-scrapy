"""
Depth Spider Middleware
深度爬虫中间件

This middleware tracks the depth of requests and can be used to limit the maximum
depth of crawls. It also adjusts request priorities based on depth and collects
depth statistics.
此中间件跟踪请求的深度，可用于限制爬取的最大深度。它还根据深度调整请求优先级
并收集深度统计信息。
"""

from aioscrapy.http import Request
from aioscrapy.utils.log import logger


class DepthMiddleware:
    """
    Spider middleware to track the depth of requests.
    用于跟踪请求深度的爬虫中间件。

    This middleware tracks how many nested links the crawler has followed from the
    initial request (depth). It can be used to limit the maximum depth of crawls,
    adjust request priorities based on depth, and collect depth statistics.
    此中间件跟踪爬虫从初始请求开始已经跟随了多少层嵌套链接（深度）。它可用于限制
    爬取的最大深度，根据深度调整请求优先级，并收集深度统计信息。
    """

    def __init__(self, maxdepth, stats, verbose_stats=False, prio=1):
        """
        Initialize the depth middleware.
        初始化深度中间件。

        Args:
            maxdepth: Maximum allowed depth. If None or 0, no limit is imposed.
                     允许的最大深度。如果为None或0，则不施加限制。
            stats: Stats collector instance.
                  统计收集器实例。
            verbose_stats: Whether to collect detailed stats for each depth level.
                          是否收集每个深度级别的详细统计信息。
                          Defaults to False.
                          默认为False。
            prio: Priority adjustment per depth level.
                 每个深度级别的优先级调整。
                 Defaults to 1.
                 默认为1。
        """
        # Maximum allowed depth
        # 允许的最大深度
        self.maxdepth = maxdepth

        # Stats collector instance
        # 统计收集器实例
        self.stats = stats

        # Whether to collect detailed stats for each depth level
        # 是否收集每个深度级别的详细统计信息
        self.verbose_stats = verbose_stats

        # Priority adjustment per depth level
        # 每个深度级别的优先级调整
        self.prio = prio

    @classmethod
    def from_crawler(cls, crawler):
        """
        Create a DepthMiddleware instance from a crawler.
        从爬虫创建DepthMiddleware实例。

        This is the factory method used by AioScrapy to create the middleware.
        这是AioScrapy用于创建中间件的工厂方法。

        Args:
            crawler: The crawler that will use this middleware.
                    将使用此中间件的爬虫。

        Returns:
            DepthMiddleware: A new DepthMiddleware instance.
                            一个新的DepthMiddleware实例。
        """
        # Get settings from crawler
        # 从爬虫获取设置
        settings = crawler.settings

        # Get maximum depth from settings
        # 从设置获取最大深度
        maxdepth = settings.getint('DEPTH_LIMIT')

        # Get verbose stats setting
        # 获取详细统计设置
        verbose = settings.getbool('DEPTH_STATS_VERBOSE')

        # Get priority adjustment setting
        # 获取优先级调整设置
        prio = settings.getint('DEPTH_PRIORITY')

        # Create and return a new instance
        # 创建并返回一个新实例
        return cls(maxdepth, crawler.stats, verbose, prio)

    async def process_spider_output(self, response, result, spider):
        """
        Process the spider output to track request depth.
        处理爬虫输出以跟踪请求深度。

        This method processes each request yielded by the spider, tracks its depth,
        adjusts its priority, and filters out requests that exceed the maximum depth.
        此方法处理爬虫产生的每个请求，跟踪其深度，调整其优先级，并过滤掉超过最大深度的请求。

        Args:
            response: The response being processed.
                     正在处理的响应。
            result: The result returned by the spider.
                   爬虫返回的结果。
            spider: The spider that generated the result.
                   生成结果的爬虫。

        Returns:
            An async generator yielding filtered requests.
            一个产生过滤后请求的异步生成器。
        """
        def _filter(request):
            """
            Filter function to process and possibly filter out requests based on depth.
            基于深度处理并可能过滤掉请求的过滤函数。

            Args:
                request: The request to process.
                         要处理的请求。

            Returns:
                bool: True if the request should be kept, False if it should be filtered out.
                     如果应保留请求，则为True；如果应过滤掉请求，则为False。
            """
            # Only process Request objects
            # 只处理Request对象
            if isinstance(request, Request):
                # Calculate depth of this request (parent depth + 1)
                # 计算此请求的深度（父深度 + 1）
                depth = response.meta['depth'] + 1

                # Store depth in request metadata
                # 将深度存储在请求元数据中
                request.meta['depth'] = depth

                # Adjust priority based on depth if enabled
                # 如果启用，则根据深度调整优先级
                if self.prio:
                    request.priority -= depth * self.prio

                # Check if request exceeds maximum depth
                # 检查请求是否超过最大深度
                if self.maxdepth and depth > self.maxdepth:
                    # Log ignored request
                    # 记录被忽略的请求
                    logger.debug("Ignoring link (depth > %(maxdepth)d): %(requrl)s " % {
                        'maxdepth': self.maxdepth, 'requrl': request.url
                    })
                    # Filter out this request
                    # 过滤掉此请求
                    return False
                else:
                    # Update depth statistics
                    # 更新深度统计信息
                    if self.verbose_stats:
                        # Increment count for this depth level
                        # 增加此深度级别的计数
                        self.stats.inc_value(f'request_depth_count/{depth}',
                                             spider=spider)

                    # Update maximum depth reached
                    # 更新达到的最大深度
                    self.stats.max_value('request_depth_max', depth,
                                         spider=spider)
            # Keep all non-Request objects and requests that didn't exceed max depth
            # 保留所有非Request对象和未超过最大深度的请求
            return True

        # Handle the base case (initial response with no depth)
        # 处理基本情况（没有深度的初始响应）
        if 'depth' not in response.meta:
            # Set depth to 0 for the initial response
            # 为初始响应设置深度为0
            response.meta['depth'] = 0

            # Update depth statistics for depth 0
            # 更新深度0的深度统计信息
            if self.verbose_stats:
                self.stats.inc_value('request_depth_count/0', spider=spider)

        # Filter the results using the _filter function
        # 使用_filter函数过滤结果
        return (r async for r in result or () if _filter(r))
