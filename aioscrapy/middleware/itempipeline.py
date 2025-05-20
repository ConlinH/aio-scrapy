"""
Item Pipeline Manager Module
项目管道管理器模块

This module provides the ItemPipelineManager class, which manages the execution
of item pipeline components. Item pipelines are components that process items
after they have been extracted by spiders, typically for cleaning, validation,
persistence, or other post-processing tasks.
此模块提供了ItemPipelineManager类，用于管理项目管道组件的执行。项目管道是
在项目被爬虫提取后处理项目的组件，通常用于清洗、验证、持久化或其他后处理任务。

Item pipelines are loaded from the ITEM_PIPELINES setting and are executed in
the order specified by their priority values. Each pipeline component can process
an item and either return it for further processing, drop it, or raise an exception.
项目管道从ITEM_PIPELINES设置加载，并按照其优先级值指定的顺序执行。每个管道组件
可以处理一个项目，并返回它以供进一步处理、丢弃它或引发异常。
"""
from aioscrapy.middleware.absmanager import AbsMiddlewareManager
from aioscrapy.utils.conf import build_component_list


class ItemPipelineManager(AbsMiddlewareManager):
    """
    Manager for item pipeline components.
    项目管道组件的管理器。

    This class manages the execution of item pipeline components, which process items
    after they have been extracted by spiders. It inherits from AbsMiddlewareManager
    and implements the specific behavior for item pipelines.
    此类管理项目管道组件的执行，这些组件在项目被爬虫提取后进行处理。它继承自
    AbsMiddlewareManager，并实现了项目管道的特定行为。

    Item pipelines are executed in the order specified by their priority values in
    the ITEM_PIPELINES setting. Each pipeline can process an item and either return
    it for further processing, drop it, or raise an exception.
    项目管道按照ITEM_PIPELINES设置中指定的优先级值顺序执行。每个管道可以处理一个
    项目，并返回它以供进一步处理、丢弃它或引发异常。
    """

    # Name of the component
    # 组件的名称
    component_name = 'item pipeline'

    @classmethod
    def _get_mwlist_from_settings(cls, settings):
        """
        Get the list of item pipeline classes from settings.
        从设置中获取项目管道类列表。

        This method implements the abstract method from AbsMiddlewareManager.
        It retrieves the list of item pipeline classes from the ITEM_PIPELINES setting.
        此方法实现了AbsMiddlewareManager中的抽象方法。它从ITEM_PIPELINES设置中
        检索项目管道类列表。

        Args:
            settings: The settings object.
                     设置对象。

        Returns:
            list: A list of item pipeline class paths.
                 项目管道类路径列表。
        """
        # Build component list from ITEM_PIPELINES setting
        # 从ITEM_PIPELINES设置构建组件列表
        return build_component_list(settings.getwithbase('ITEM_PIPELINES'))

    def _add_middleware(self, pipe):
        """
        Add a pipeline instance to the manager.
        将管道实例添加到管理器。

        This method overrides the method from AbsMiddlewareManager to register
        the process_item method of item pipelines. It first calls the parent method
        to register open_spider and close_spider methods if they exist.
        此方法覆盖了AbsMiddlewareManager中的方法，以注册项目管道的process_item方法。
        它首先调用父方法来注册open_spider和close_spider方法（如果存在）。

        Args:
            pipe: The pipeline instance to add.
                 要添加的管道实例。
        """
        # Call parent method to register open_spider and close_spider methods
        # 调用父方法来注册open_spider和close_spider方法
        super()._add_middleware(pipe)

        # Register process_item method if it exists
        # 如果存在，则注册process_item方法
        if hasattr(pipe, 'process_item'):
            self.methods['process_item'].append(pipe.process_item)

    async def process_item(self, item, spider):
        """
        Process an item through all registered process_item methods.
        通过所有已注册的process_item方法处理项目。

        This method calls each pipeline's process_item method in the order they
        were registered. The result of each pipeline is passed to the next one
        in a chain, allowing pipelines to modify the item or drop it by returning None.
        此方法按照它们注册的顺序调用每个管道的process_item方法。每个管道的结果
        以链式方式传递给下一个管道，允许管道修改项目或通过返回None来丢弃它。

        Args:
            item: The item to process.
                 要处理的项目。
            spider: The spider that generated the item.
                   生成项目的爬虫。

        Returns:
            The processed item, or None if it was dropped by a pipeline.
            处理后的项目，如果被管道丢弃则为None。
        """
        # Process the item through the chain of process_item methods
        # 通过process_item方法链处理项目
        return await self._process_chain('process_item', item, spider)
