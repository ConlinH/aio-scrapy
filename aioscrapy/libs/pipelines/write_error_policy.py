"""
Database pipeline write error policies.
数据库管道写入错误策略。

The built-in connection policy and user-defined error matchers are kept here so
the batch persistence flow does not need to know individual database errors.
内置连接异常策略和用户自定义错误匹配器集中在此处，批量持久化流程无需了解具体数据库异常。
"""

import errno

from aioscrapy.utils.misc import load_object


MYSQL_CONNECTION_ERROR_CODES = {2002, 2003, 2006, 2013, 2055}
SOCKET_ERROR_CODES = {
    errno.ECONNABORTED,
    errno.ECONNREFUSED,
    errno.ECONNRESET,
    errno.EHOSTUNREACH,
    errno.ENETUNREACH,
    errno.EPIPE,
    errno.ETIMEDOUT,
}

CONNECTION_ERROR_NAMES = {
    "AutoReconnect",
    "CannotConnectNowError",
    "ConnectionDoesNotExistError",
    "ConnectionFailure",
    "ConnectionFailureError",
    "NetworkTimeout",
    "PostgresConnectionError",
    "ServerSelectionTimeoutError",
    "TooManyConnectionsError",
    "gaierror",
}


def iter_exception_chain(exception):
    """
    Yield an exception and its explicit or implicit causes once.
    依次返回异常及其显式或隐式原因，并避免循环引用。
    """
    seen = set()
    current = exception
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        yield current
        current = current.__cause__ or current.__context__


def is_database_connection_error(exception):
    """
    Return whether an exception represents an unavailable database connection.
    判断异常是否表示数据库连接不可用。
    """
    for current in iter_exception_chain(exception):
        if isinstance(current, (ConnectionError, TimeoutError)):
            return True

        error_class = current.__class__
        error_name = error_class.__name__
        error_module = error_class.__module__

        if error_name in CONNECTION_ERROR_NAMES:
            return True

        if isinstance(current, OSError) and current.errno in SOCKET_ERROR_CODES:
            return True

        if error_module.startswith(("aiomysql", "pymysql")):
            if error_name == "InterfaceError":
                return True
            if error_name == "OperationalError" and current.args:
                return current.args[0] in MYSQL_CONNECTION_ERROR_CODES

        if error_module.startswith("redis.exceptions") and error_name in {"ConnectionError", "TimeoutError"}:
            return True

    return False


class WriteErrorPolicy:
    """
    Match write errors that should pause the spider and retry the current batch.
    匹配需要暂停爬虫并重试当前批次的写入异常。

    Besides the built-in connection matcher, projects can register exception
    classes or checker callables through settings without changing pipeline code.
    除内置连接异常匹配器外，项目可通过配置注册异常类或判定函数，无需修改管道代码。
    """

    def __init__(
        self,
        pause_on_connection_error=False,
        error_types=None,
        error_checkers=None,
    ):
        """
        Initialize the write-error policy.
        初始化写入错误策略。
        """
        self.pause_on_connection_error = pause_on_connection_error
        self.error_types = self._load_error_types(error_types or [])
        self.error_checkers = self._load_error_checkers(error_checkers or [])

    @classmethod
    def from_settings(cls, settings):
        """
        Build a policy from database pipeline settings.
        从数据库管道配置创建策略。
        """
        return cls(
            pause_on_connection_error=settings.getbool(
                'DB_PIPELINE_PAUSE_ON_CONNECTION_ERROR', False
            ),
            error_types=cls._get_setting_list(
                settings, 'DB_PIPELINE_PAUSE_ON_WRITE_ERROR_TYPES'
            ),
            error_checkers=cls._get_setting_list(
                settings, 'DB_PIPELINE_PAUSE_ON_WRITE_ERROR_CHECKERS'
            ),
        )

    def match(self, exception):
        """
        Return the matching policy name, or ``None`` when retry is not allowed.
        返回匹配的策略名称；不应重试时返回``None``。
        """
        if (
            self.pause_on_connection_error
            and is_database_connection_error(exception)
        ):
            return 'pause_on_connection_error'

        if self.error_types and any(
            isinstance(current, self.error_types)
            for current in iter_exception_chain(exception)
        ):
            return 'configured_error_type'

        for checker in self.error_checkers:
            if checker(exception):
                return getattr(checker, '__name__', checker.__class__.__name__)

        return None

    @staticmethod
    def _load_error_types(values):
        """
        Load and validate configured exception classes.
        加载并校验配置的异常类。
        """
        error_types = []
        for value in values:
            if isinstance(value, str):
                value = value.strip()
                if not value:
                    continue
                error_type = load_object(value)
            else:
                error_type = value
            if not isinstance(error_type, type) or not issubclass(error_type, BaseException):
                raise TypeError(
                    'DB_PIPELINE_PAUSE_ON_WRITE_ERROR_TYPES entries must be '
                    'exception classes or their import paths'
                )
            error_types.append(error_type)
        return tuple(error_types)

    @staticmethod
    def _load_error_checkers(values):
        """
        Load and validate configured synchronous error checker callables.
        加载并校验配置的同步异常判定函数。
        """
        error_checkers = []
        for value in values:
            if isinstance(value, str):
                value = value.strip()
                if not value:
                    continue
                checker = load_object(value)
            else:
                checker = value
            if not callable(checker):
                raise TypeError(
                    'DB_PIPELINE_PAUSE_ON_WRITE_ERROR_CHECKERS entries must be '
                    'callables or their import paths'
                )
            error_checkers.append(checker)
        return tuple(error_checkers)

    @staticmethod
    def _get_setting_list(settings, name):
        """
        Read a list from full Settings objects and small test doubles alike.
        同时兼容完整Settings对象和简化的测试设置对象读取列表。
        """
        getlist = getattr(settings, 'getlist', None)
        if getlist is not None:
            return getlist(name, [])

        value = settings.get(name, [])
        if isinstance(value, str):
            return [entry.strip() for entry in value.split(',') if entry.strip()]
        return list(value or [])
