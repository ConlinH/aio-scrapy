"""
The Extension Manager
扩展管理器

This module provides the ExtensionManager class, which manages the loading and
execution of extensions. Extensions are components that can hook into various
parts of the Scrapy process to add functionality or modify behavior.
此模块提供了ExtensionManager类，用于管理扩展的加载和执行。扩展是可以挂钩到
Scrapy流程的各个部分以添加功能或修改行为的组件。

Extensions are loaded from the EXTENSIONS setting and can be enabled or disabled
through this setting. They can connect to signals to execute code at specific
points in the crawling process.
扩展从EXTENSIONS设置加载，可以通过此设置启用或禁用。它们可以连接到信号，
以在爬取过程的特定点执行代码。
"""
from aioscrapy.middleware.absmanager import AbsMiddlewareManager
from aioscrapy.utils.conf import build_component_list


class ExtensionManager(AbsMiddlewareManager):
    """
    Manager for extension components.
    扩展组件的管理器。

    This class manages the loading and execution of extensions. It inherits from
    AbsMiddlewareManager and implements the specific behavior for extensions.
    Extensions are components that can hook into various parts of the Scrapy
    process to add functionality or modify behavior.
    此类管理扩展的加载和执行。它继承自AbsMiddlewareManager，并实现了扩展的特定行为。
    扩展是可以挂钩到Scrapy流程的各个部分以添加功能或修改行为的组件。

    Extensions typically connect to signals to execute code at specific points in
    the crawling process. They can be enabled or disabled through the EXTENSIONS
    setting.
    扩展通常连接到信号，以在爬取过程的特定点执行代码。它们可以通过EXTENSIONS设置
    启用或禁用。
    """

    # Name of the component
    # 组件的名称
    component_name = 'extension'

    @classmethod
    def _get_mwlist_from_settings(cls, settings):
        """
        Get the list of extension classes from settings.
        从设置中获取扩展类列表。

        This method implements the abstract method from AbsMiddlewareManager.
        It retrieves the list of extension classes from the EXTENSIONS setting.
        此方法实现了AbsMiddlewareManager中的抽象方法。它从EXTENSIONS设置中检索
        扩展类列表。

        Args:
            settings: The settings object.
                     设置对象。

        Returns:
            list: A list of extension class paths.
                 扩展类路径列表。
        """
        # Build component list from EXTENSIONS setting
        # 从EXTENSIONS设置构建组件列表
        return build_component_list(settings.getwithbase('EXTENSIONS'))
