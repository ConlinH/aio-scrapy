import traceback
import warnings
from collections import defaultdict

from zope.interface import Interface, implementer

from aioscrapy.utils.misc import walk_modules
from aioscrapy.utils.spider import iter_spider_classes


class ISpiderLoader(Interface):
    """
    Interface for spider loader implementations.
    爬虫加载器实现的接口。

    This interface defines the methods that spider loader implementations
    must provide.
    此接口定义了爬虫加载器实现必须提供的方法。
    """

    def from_settings(settings):
        """
        Return an instance of the class for the given settings.
        返回给定设置的类实例。

        Args:
            settings: The settings to use for the spider loader.
                     用于爬虫加载器的设置。

        Returns:
            An instance of the spider loader.
            爬虫加载器的实例。
        """

    def load(spider_name):
        """
        Return the Spider class for the given spider name.
        返回给定爬虫名称的Spider类。

        Args:
            spider_name: The name of the spider to load.
                        要加载的爬虫的名称。

        Returns:
            The Spider class for the given spider name.
            给定爬虫名称的Spider类。

        Raises:
            KeyError: If the spider name is not found.
                     如果找不到爬虫名称。
        """

    def list():
        """
        Return a list with the names of all spiders available in the project.
        返回项目中所有可用爬虫的名称列表。

        Returns:
            A list of spider names.
            爬虫名称列表。
        """

    def find_by_request(request):
        """
        Return the list of spider names that can handle the given request.
        返回可以处理给定请求的爬虫名称列表。

        Args:
            request: The request to check.
                    要检查的请求。

        Returns:
            A list of spider names that can handle the request.
            可以处理请求的爬虫名称列表。
        """


@implementer(ISpiderLoader)
class SpiderLoader:
    """
    SpiderLoader is a class which locates and loads spiders in a aioscrapy project.
    SpiderLoader是一个定位和加载aioscrapy项目中爬虫的类。

    This class implements the ISpiderLoader interface and provides methods to
    find, load, and list spiders in a project.
    此类实现了ISpiderLoader接口，并提供了在项目中查找、加载和列出爬虫的方法。
    """

    def __init__(self, settings):
        """
        Initialize the SpiderLoader.
        初始化SpiderLoader。

        This method initializes the SpiderLoader with the given settings and
        loads all spiders from the specified modules.
        此方法使用给定的设置初始化SpiderLoader，并从指定的模块加载所有爬虫。

        Args:
            settings: The settings object containing spider loader configuration.
                     包含爬虫加载器配置的设置对象。
        """
        self.spider_modules = settings.getlist('SPIDER_MODULES')
        self.warn_only = settings.getbool('SPIDER_LOADER_WARN_ONLY')
        self._spiders = {}  # Dict of spider name -> spider class
                           # 爬虫名称 -> 爬虫类的字典
        self._found = defaultdict(list)  # Dict of spider name -> list of (module, class) locations
                                        # 爬虫名称 -> (模块, 类)位置列表的字典
        self._load_all_spiders()

    def _check_name_duplicates(self):
        """
        Check for duplicate spider names and issue warnings if found.
        检查重复的爬虫名称，如果发现则发出警告。

        This method checks if there are multiple spider classes with the same name
        and issues a warning if duplicates are found.
        此方法检查是否有多个具有相同名称的爬虫类，如果发现重复则发出警告。
        """
        dupes = []
        for name, locations in self._found.items():
            dupes.extend([
                f"  {cls} named {name!r} (in {mod})"
                for mod, cls in locations
                if len(locations) > 1
            ])

        if dupes:
            dupes_string = "\n\n".join(dupes)
            warnings.warn(
                "There are several spiders with the same name:\n\n"
                f"{dupes_string}\n\n  This can cause unexpected behavior.",
                category=UserWarning,
            )

    def _load_spiders(self, module):
        """
        Load spiders from a given module.
        从给定模块加载爬虫。

        This method finds all spider classes in the given module and adds them
        to the internal dictionaries.
        此方法查找给定模块中的所有爬虫类，并将它们添加到内部字典中。

        Args:
            module: The module to load spiders from.
                   要从中加载爬虫的模块。
        """
        for spcls in iter_spider_classes(module):
            self._found[spcls.name].append((module.__name__, spcls.__name__))
            self._spiders[spcls.name] = spcls

    def _load_all_spiders(self):
        """
        Load all spiders from all modules specified in SPIDER_MODULES setting.
        从SPIDER_MODULES设置中指定的所有模块加载所有爬虫。

        This method walks through all the modules specified in the SPIDER_MODULES
        setting, loads all spiders from them, and checks for duplicate names.
        此方法遍历SPIDER_MODULES设置中指定的所有模块，从中加载所有爬虫，并检查重复的名称。

        If an import error occurs and SPIDER_LOADER_WARN_ONLY is True, a warning
        is issued instead of raising the exception.
        如果发生导入错误且SPIDER_LOADER_WARN_ONLY为True，则发出警告而不是引发异常。
        """
        for name in self.spider_modules:
            try:
                for module in walk_modules(name):
                    self._load_spiders(module)
            except ImportError:
                if self.warn_only:
                    warnings.warn(
                        f"\n{traceback.format_exc()}Could not load spiders "
                        f"from module '{name}'. "
                        "See above traceback for details.",
                        category=RuntimeWarning,
                    )
                else:
                    raise
        self._check_name_duplicates()

    @classmethod
    def from_settings(cls, settings):
        """
        Create a SpiderLoader instance from settings.
        从设置创建SpiderLoader实例。

        This is a factory method that creates a new SpiderLoader instance
        with the given settings.
        这是一个工厂方法，使用给定的设置创建一个新的SpiderLoader实例。

        Args:
            settings: The settings to use for the spider loader.
                     用于爬虫加载器的设置。

        Returns:
            A new SpiderLoader instance.
            一个新的SpiderLoader实例。
        """
        return cls(settings)

    def load(self, spider_name):
        """
        Return the Spider class for the given spider name.
        返回给定爬虫名称的Spider类。

        This method looks up the spider class by name in the internal dictionary.
        此方法在内部字典中按名称查找爬虫类。

        Args:
            spider_name: The name of the spider to load.
                        要加载的爬虫的名称。

        Returns:
            The Spider class for the given spider name.
            给定爬虫名称的Spider类。

        Raises:
            KeyError: If the spider name is not found.
                     如果找不到爬虫名称。
        """
        try:
            return self._spiders[spider_name]
        except KeyError:
            raise KeyError(f"Spider not found: {spider_name}")

    def find_by_request(self, request):
        """
        Return the list of spider names that can handle the given request.
        返回可以处理给定请求的爬虫名称列表。

        This method checks each spider's handles_request method to determine
        if it can handle the given request.
        此方法检查每个爬虫的handles_request方法，以确定它是否可以处理给定的请求。

        Args:
            request: The request to check.
                    要检查的请求。

        Returns:
            A list of spider names that can handle the request.
            可以处理请求的爬虫名称列表。
        """
        return [
            name for name, cls in self._spiders.items()
            if cls.handles_request(request)
        ]

    def list(self):
        """
        Return a list with the names of all spiders available in the project.
        返回项目中所有可用爬虫的名称列表。

        This method returns a list of all spider names that have been loaded
        by the spider loader.
        此方法返回已由爬虫加载器加载的所有爬虫名称的列表。

        Returns:
            A list of spider names.
            爬虫名称列表。
        """
        return list(self._spiders.keys())
