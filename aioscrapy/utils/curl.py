"""
cURL command parsing utilities for aioscrapy.
aioscrapy的cURL命令解析实用工具。

This module provides utilities for converting cURL commands to aioscrapy Request objects.
It parses cURL command syntax and extracts relevant parameters like headers, cookies,
authentication, and request body.
此模块提供了将cURL命令转换为aioscrapy Request对象的实用工具。
它解析cURL命令语法并提取相关参数，如标头、cookie、身份验证和请求正文。
"""

import argparse
import warnings
from shlex import split
from http.cookies import SimpleCookie
from urllib.parse import urlparse

from w3lib.http import basic_auth_header


class CurlParser(argparse.ArgumentParser):
    """
    Custom ArgumentParser for parsing cURL commands.
    用于解析cURL命令的自定义ArgumentParser。

    This class extends the standard ArgumentParser to provide better error handling
    for cURL command parsing. Instead of printing to stderr and exiting, it raises
    a ValueError with a descriptive message when parsing fails.
    此类扩展了标准ArgumentParser，为cURL命令解析提供更好的错误处理。
    当解析失败时，它会引发带有描述性消息的ValueError，而不是打印到stderr并退出。
    """

    def error(self, message):
        """
        Override the default error method to raise ValueError instead of exiting.
        覆盖默认的error方法，引发ValueError而不是退出。

        Args:
            message: The error message from the ArgumentParser.
                    来自ArgumentParser的错误消息。

        Raises:
            ValueError: Always raised with a descriptive error message.
                       始终引发带有描述性错误消息的ValueError。
        """
        error_msg = f'There was an error parsing the curl command: {message}'
        raise ValueError(error_msg)


# Create a parser instance for cURL commands
# 创建用于cURL命令的解析器实例
curl_parser = CurlParser()

# Add arguments for the main cURL options we want to support
# 添加我们想要支持的主要cURL选项的参数
curl_parser.add_argument('url')  # The target URL (positional argument)
curl_parser.add_argument('-H', '--header', dest='headers', action='append')  # HTTP headers
curl_parser.add_argument('-X', '--request', dest='method')  # HTTP method (GET, POST, etc.)
curl_parser.add_argument('-d', '--data', '--data-raw', dest='data')  # Request body data
curl_parser.add_argument('-u', '--user', dest='auth')  # Basic authentication credentials


# List of cURL arguments that can be safely ignored
# These arguments don't affect the Request object we're building
# cURL参数列表，可以安全地忽略
# 这些参数不会影响我们正在构建的Request对象
safe_to_ignore_arguments = [
    ['--compressed'],
    # `--compressed` argument is not safe to ignore, but it's included here
    # because the `HttpCompressionMiddleware` is enabled by default
    # `--compressed`参数实际上不安全忽略，但它包含在这里
    # 因为`HttpCompressionMiddleware`默认启用
    ['-s', '--silent'],  # Don't show progress meter or error messages
    ['-v', '--verbose'],  # Make the operation more talkative
    ['-#', '--progress-bar']  # Display transfer progress as a progress bar
]

# Add all the safe-to-ignore arguments to the parser
# 将所有可以安全忽略的参数添加到解析器
for argument in safe_to_ignore_arguments:
    curl_parser.add_argument(*argument, action='store_true')


def _parse_headers_and_cookies(parsed_args):
    """
    Extract headers and cookies from parsed cURL arguments.
    从解析的cURL参数中提取标头和cookie。

    This internal helper function processes the headers from cURL arguments,
    separating regular headers from cookies. It also handles basic authentication
    by converting it to an Authorization header.
    此内部辅助函数处理来自cURL参数的标头，将常规标头与cookie分开。
    它还通过将基本身份验证转换为Authorization标头来处理基本身份验证。

    Args:
        parsed_args: The parsed arguments from the cURL command.
                    来自cURL命令的解析参数。

    Returns:
        tuple: A tuple containing:
              包含以下内容的元组：
              - headers (list): List of (name, value) tuples for HTTP headers.
                              HTTP标头的(名称, 值)元组列表。
              - cookies (dict): Dictionary of cookie names and values.
                              cookie名称和值的字典。
    """
    headers = []
    cookies = {}

    # Process each header from the cURL command
    # 处理来自cURL命令的每个标头
    for header in parsed_args.headers or ():
        # Split the header into name and value
        # 将标头分成名称和值
        name, val = header.split(':', 1)
        name = name.strip()
        val = val.strip()

        # Special handling for Cookie headers
        # 对Cookie标头的特殊处理
        if name.title() == 'Cookie':
            # Parse the cookie string and add each cookie to the cookies dict
            # 解析cookie字符串并将每个cookie添加到cookies字典
            for name, morsel in SimpleCookie(val).items():
                cookies[name] = morsel.value
        else:
            # Add regular headers to the headers list
            # 将常规标头添加到标头列表
            headers.append((name, val))

    # Handle basic authentication if provided
    # 如果提供了基本身份验证，则处理它
    if parsed_args.auth:
        # Split the auth string into username and password
        # 将auth字符串分成用户名和密码
        user, password = parsed_args.auth.split(':', 1)
        # Create and add the Authorization header
        # 创建并添加Authorization标头
        headers.append(('Authorization', basic_auth_header(user, password)))

    return headers, cookies


def curl_to_request_kwargs(curl_command, ignore_unknown_options=True):
    """
    Convert a cURL command to Request keyword arguments.
    将cURL命令转换为Request关键字参数。

    This function parses a cURL command string and converts it to a dictionary
    of keyword arguments that can be used to create an aioscrapy Request object.
    It handles common cURL options like headers, cookies, method, data, and
    authentication.
    此函数解析cURL命令字符串，并将其转换为可用于创建aioscrapy Request对象的
    关键字参数字典。它处理常见的cURL选项，如标头、cookie、方法、数据和身份验证。

    Args:
        curl_command: String containing the complete curl command.
                     包含完整curl命令的字符串。
        ignore_unknown_options: If True, only a warning is emitted when cURL options
                               are unknown. Otherwise raises an error.
                               如果为True，则在cURL选项未知时只发出警告。
                               否则引发错误。
                               Defaults to True.
                               默认为True。

    Returns:
        dict: Dictionary of Request keyword arguments, which may include:
              Request关键字参数的字典，可能包括：
              - method: HTTP method (GET, POST, etc.)
                       HTTP方法（GET、POST等）
              - url: The target URL
                    目标URL
              - headers: List of (name, value) header tuples
                        (名称, 值)标头元组的列表
              - cookies: Dictionary of cookie names and values
                        cookie名称和值的字典
              - body: Request body data
                     请求正文数据

    Raises:
        ValueError: If the command doesn't start with 'curl', or if unknown options
                   are encountered and ignore_unknown_options is False.
                   如果命令不以'curl'开头，或者如果遇到未知选项且
                   ignore_unknown_options为False。

    Example:
        >>> kwargs = curl_to_request_kwargs('curl -X POST "http://example.com" -H "Content-Type: application/json" -d \'{"key": "value"}\'')
        >>> request = Request(**kwargs)
    """
    # Split the command string into arguments
    # 将命令字符串分割成参数
    curl_args = split(curl_command)

    # Verify that the command starts with 'curl'
    # 验证命令以'curl'开头
    if curl_args[0] != 'curl':
        raise ValueError('A curl command must start with "curl"')

    # Parse the arguments, separating known from unknown
    # 解析参数，将已知参数与未知参数分开
    parsed_args, argv = curl_parser.parse_known_args(curl_args[1:])

    # Handle unknown arguments
    # 处理未知参数
    if argv:
        msg = f'Unrecognized options: {", ".join(argv)}'
        if ignore_unknown_options:
            warnings.warn(msg)
        else:
            raise ValueError(msg)

    # Get the URL from the parsed arguments
    # 从解析的参数中获取URL
    url = parsed_args.url

    # curl automatically prepends 'http' if the scheme is missing, but Request
    # needs the scheme to work, so we add it if necessary
    # curl在方案缺失时自动添加'http'，但Request需要方案才能工作，
    # 因此我们在必要时添加它
    parsed_url = urlparse(url)
    if not parsed_url.scheme:
        url = 'http://' + url

    # Get the HTTP method or default to GET
    # 获取HTTP方法或默认为GET
    method = parsed_args.method or 'GET'

    # Start building the result dictionary
    # 开始构建结果字典
    result = {'method': method.upper(), 'url': url}

    # Extract headers and cookies from the parsed arguments
    # 从解析的参数中提取标头和cookie
    headers, cookies = _parse_headers_and_cookies(parsed_args)

    # Add headers to the result if present
    # 如果存在，将标头添加到结果
    if headers:
        result['headers'] = headers

    # Add cookies to the result if present
    # 如果存在，将cookie添加到结果
    if cookies:
        result['cookies'] = cookies

    # Handle request body data
    # 处理请求正文数据
    if parsed_args.data:
        result['body'] = parsed_args.data

        # If data is provided but method is not specified, default to POST
        # 如果提供了数据但未指定方法，则默认为POST
        if not parsed_args.method:
            # if the "data" is specified but the "method" is not specified,
            # the default method is 'POST'
            result['method'] = 'POST'

    return result
