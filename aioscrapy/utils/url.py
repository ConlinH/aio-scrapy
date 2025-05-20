"""
URL utility functions for aioscrapy.
aioscrapy的URL实用函数。

This module contains general purpose URL functions not found in the standard
library. It provides utilities for URL parsing, manipulation, and validation
specific to web crawling needs.
此模块包含标准库中没有的通用URL函数。
它提供了特定于网络爬取需求的URL解析、操作和验证实用工具。

Some of the functions that used to be imported from this module have been moved
to the w3lib.url module. Always import those from there instead.
以前从此模块导入的一些函数已移至w3lib.url模块。
始终从那里导入这些函数。
"""
import posixpath
import re
from urllib.parse import ParseResult, urldefrag, urlparse, urlunparse

# scrapy.utils.url was moved to w3lib.url and import * ensures this
# move doesn't break old code
from w3lib.url import *  # This imports functions like any_to_uri, add_or_replace_parameter, etc.
from w3lib.url import _safe_chars, _unquotepath  # noqa: F401
from aioscrapy.utils.python import to_unicode


def url_is_from_any_domain(url, domains):
    """
    Check if a URL belongs to any of the given domains.
    检查URL是否属于给定域名中的任何一个。

    This function checks if the host part of the URL exactly matches any of the
    given domains, or if it is a subdomain of any of them. The comparison is
    case-insensitive.
    此函数检查URL的主机部分是否与给定域名中的任何一个完全匹配，
    或者它是否是其中任何一个的子域。比较不区分大小写。

    Args:
        url: The URL to check. Can be a string or a ParseResult object.
             要检查的URL。可以是字符串或ParseResult对象。
        domains: A list of domain names to check against.
                要检查的域名列表。

    Returns:
        bool: True if the URL belongs to any of the given domains, False otherwise.
              如果URL属于给定域名中的任何一个，则为True，否则为False。

    Examples:
        >>> url_is_from_any_domain("http://www.example.com/some/page.html", ["example.com"])
        True
        >>> url_is_from_any_domain("http://sub.example.com/", ["example.com"])
        True
        >>> url_is_from_any_domain("http://example.org/", ["example.com"])
        False
    """
    # Get the host part of the URL and convert to lowercase
    # 获取URL的主机部分并转换为小写
    host = parse_url(url).netloc.lower()

    # If there's no host, it's not from any domain
    # 如果没有主机，则不属于任何域名
    if not host:
        return False

    # Convert all domains to lowercase for case-insensitive comparison
    # 将所有域名转换为小写以进行不区分大小写的比较
    domains = [d.lower() for d in domains]

    # Check if the host exactly matches any domain or is a subdomain of any domain
    # 检查主机是否与任何域名完全匹配或是任何域名的子域
    return any((host == d) or (host.endswith(f'.{d}')) for d in domains)


def url_is_from_spider(url, spider):
    """
    Check if a URL belongs to the given spider.
    检查URL是否属于给定的爬虫。

    This function checks if the URL belongs to the domains that the spider
    is allowed to crawl. It considers both the spider's name and its
    'allowed_domains' attribute (if it exists).
    此函数检查URL是否属于爬虫允许爬取的域名。
    它同时考虑爬虫的名称和其'allowed_domains'属性（如果存在）。

    Args:
        url: The URL to check. Can be a string or a ParseResult object.
             要检查的URL。可以是字符串或ParseResult对象。
        spider: The spider object to check against.
               要检查的爬虫对象。

    Returns:
        bool: True if the URL belongs to the spider's domains, False otherwise.
              如果URL属于爬虫的域名，则为True，否则为False。
    """
    # Check if the URL belongs to either the spider's name or any of its allowed domains
    # 检查URL是否属于爬虫的名称或其任何允许的域名
    return url_is_from_any_domain(url, [spider.name] + list(getattr(spider, 'allowed_domains', [])))


def url_has_any_extension(url, extensions):
    """
    Check if a URL has any of the given extensions.
    检查URL是否具有给定扩展名中的任何一个。

    This function extracts the file extension from the URL path and checks
    if it matches any of the provided extensions. The comparison is case-insensitive.
    此函数从URL路径中提取文件扩展名，并检查它是否与提供的任何扩展名匹配。
    比较不区分大小写。

    Args:
        url: The URL to check. Can be a string or a ParseResult object.
             要检查的URL。可以是字符串或ParseResult对象。
        extensions: A list of file extensions to check against (including the dot).
                   要检查的文件扩展名列表（包括点）。

    Returns:
        bool: True if the URL has any of the given extensions, False otherwise.
              如果URL具有给定扩展名中的任何一个，则为True，否则为False。

    Examples:
        >>> url_has_any_extension("http://example.com/file.pdf", ['.pdf', '.doc'])
        True
        >>> url_has_any_extension("http://example.com/file.PDF", ['.pdf'])
        True
        >>> url_has_any_extension("http://example.com/file.txt", ['.pdf', '.doc'])
        False
    """
    # Extract the file extension from the URL path and check if it's in the list
    # 从URL路径中提取文件扩展名，并检查它是否在列表中
    return posixpath.splitext(parse_url(url).path)[1].lower() in extensions


def parse_url(url, encoding=None):
    """
    Parse a URL into its components.
    将URL解析为其组成部分。

    This function parses a URL into its components using urllib.parse.urlparse.
    If the input is already a ParseResult object, it is returned unchanged.
    If the input is a string or bytes, it is first converted to unicode.
    此函数使用urllib.parse.urlparse将URL解析为其组成部分。
    如果输入已经是ParseResult对象，则原样返回。
    如果输入是字符串或字节，则首先将其转换为unicode。

    Args:
        url: The URL to parse. Can be a string, bytes, or ParseResult object.
             要解析的URL。可以是字符串、字节或ParseResult对象。
        encoding: The encoding to use for decoding bytes. Defaults to 'utf-8'.
                 用于解码字节的编码。默认为'utf-8'。

    Returns:
        ParseResult: A named tuple with URL components: scheme, netloc, path,
                    params, query, and fragment.
                    包含URL组件的命名元组：scheme、netloc、path、
                    params、query和fragment。
    """
    # If the URL is already parsed, return it as is
    # 如果URL已经解析，则原样返回
    if isinstance(url, ParseResult):
        return url
    # Otherwise, convert to unicode and parse
    # 否则，转换为unicode并解析
    return urlparse(to_unicode(url, encoding))


def escape_ajax(url):
    """
    Convert AJAX URLs to crawlable URLs according to Google's specification.
    根据Google的规范将AJAX URL转换为可爬取的URL。

    This function implements Google's "AJAX crawling scheme" which allows
    search engines to crawl AJAX-based pages. It converts fragment identifiers
    that start with an exclamation mark (!) to query parameters with the
    "_escaped_fragment_" key.
    此函数实现了Google的"AJAX爬取方案"，该方案允许搜索引擎爬取基于AJAX的页面。
    它将以感叹号(!)开头的片段标识符转换为带有"_escaped_fragment_"键的查询参数。

    See: https://developers.google.com/webmasters/ajax-crawling/docs/getting-started

    Args:
        url: The URL to convert.
             要转换的URL。

    Returns:
        str: The crawlable URL with _escaped_fragment_ parameter if the URL
             contains an AJAX fragment, or the original URL otherwise.
             如果URL包含AJAX片段，则返回带有_escaped_fragment_参数的可爬取URL，
             否则返回原始URL。

    Examples:
        >>> escape_ajax("www.example.com/ajax.html#!key=value")
        'www.example.com/ajax.html?_escaped_fragment_=key%3Dvalue'
        >>> escape_ajax("www.example.com/ajax.html?k1=v1&k2=v2#!key=value")
        'www.example.com/ajax.html?k1=v1&k2=v2&_escaped_fragment_=key%3Dvalue'
        >>> escape_ajax("www.example.com/ajax.html?#!key=value")
        'www.example.com/ajax.html?_escaped_fragment_=key%3Dvalue'
        >>> escape_ajax("www.example.com/ajax.html#!")
        'www.example.com/ajax.html?_escaped_fragment_='

        URLs that are not "AJAX crawlable" (according to Google) returned as-is:

        >>> escape_ajax("www.example.com/ajax.html#key=value")
        'www.example.com/ajax.html#key=value'
        >>> escape_ajax("www.example.com/ajax.html#")
        'www.example.com/ajax.html#'
        >>> escape_ajax("www.example.com/ajax.html")
        'www.example.com/ajax.html'
    """
    # Split the URL into the part before the fragment and the fragment itself
    # 将URL拆分为片段之前的部分和片段本身
    defrag, frag = urldefrag(url)

    # If the fragment doesn't start with '!', it's not an AJAX URL
    # 如果片段不以'!'开头，则它不是AJAX URL
    if not frag.startswith('!'):
        return url

    # Convert the AJAX URL to a crawlable URL by adding the _escaped_fragment_ parameter
    # 通过添加_escaped_fragment_参数将AJAX URL转换为可爬取的URL
    return add_or_replace_parameter(defrag, '_escaped_fragment_', frag[1:])


def add_http_if_no_scheme(url):
    """
    Add http as the default scheme if it is missing from the URL.
    如果URL中缺少协议，则添加http作为默认协议。

    This function checks if the URL already has a scheme (like http://, https://, ftp://).
    If not, it adds 'http:' or 'http://' depending on whether the URL already has a netloc.
    此函数检查URL是否已有协议（如http://、https://、ftp://）。
    如果没有，它会添加'http:'或'http://'，具体取决于URL是否已有网络位置。

    Args:
        url: The URL to check and possibly modify.
             要检查并可能修改的URL。

    Returns:
        str: The URL with a scheme, either the original one or with 'http' added.
             带有协议的URL，可能是原始协议或添加了'http'。

    Examples:
        >>> add_http_if_no_scheme("example.com")
        'http://example.com'
        >>> add_http_if_no_scheme("http://example.com")
        'http://example.com'
        >>> add_http_if_no_scheme("https://example.com")
        'https://example.com'
    """
    # Check if the URL already has a scheme
    # 检查URL是否已有协议
    match = re.match(r"^\w+://", url, flags=re.I)
    if not match:
        # Parse the URL to determine if it has a netloc
        # 解析URL以确定它是否有网络位置
        parts = urlparse(url)
        # Add the appropriate http scheme
        # 添加适当的http协议
        scheme = "http:" if parts.netloc else "http://"
        url = scheme + url

    return url


def _is_posix_path(string):
    """
    Check if a string looks like a POSIX filesystem path.
    检查字符串是否看起来像POSIX文件系统路径。

    This function uses a regular expression to check if the string matches
    common patterns for POSIX filesystem paths, such as absolute paths,
    relative paths, and paths with home directory references.
    此函数使用正则表达式检查字符串是否匹配POSIX文件系统路径的常见模式，
    如绝对路径、相对路径和带有主目录引用的路径。

    Args:
        string: The string to check.
               要检查的字符串。

    Returns:
        bool: True if the string looks like a POSIX path, False otherwise.
              如果字符串看起来像POSIX路径，则为True，否则为False。
    """
    return bool(
        re.match(
            r'''
            ^                   # start with...
            (
                \.              # ...a single dot,
                (
                    \. | [^/\.]+  # optionally followed by
                )?                # either a second dot or some characters
                |
                ~   # $HOME
            )?      # optional match of ".", ".." or ".blabla"
            /       # at least one "/" for a file path,
            .       # and something after the "/"
            ''',
            string,
            flags=re.VERBOSE,
        )
    )


def _is_windows_path(string):
    """
    Check if a string looks like a Windows filesystem path.
    检查字符串是否看起来像Windows文件系统路径。

    This function uses a regular expression to check if the string matches
    common patterns for Windows filesystem paths, such as drive letters (C:\)
    or UNC paths (\\server\share).
    此函数使用正则表达式检查字符串是否匹配Windows文件系统路径的常见模式，
    如驱动器号（C:\）或UNC路径（\\server\share）。

    Args:
        string: The string to check.
               要检查的字符串。

    Returns:
        bool: True if the string looks like a Windows path, False otherwise.
              如果字符串看起来像Windows路径，则为True，否则为False。
    """
    return bool(
        re.match(
            r'''
            ^
            (
                [a-z]:\\        # Drive letter followed by :\
                | \\\\          # Or UNC path starting with \\
            )
            ''',
            string,
            flags=re.IGNORECASE | re.VERBOSE,
        )
    )


def _is_filesystem_path(string):
    """
    Check if a string looks like a filesystem path (either POSIX or Windows).
    检查字符串是否看起来像文件系统路径（POSIX或Windows）。

    This function combines the checks for both POSIX and Windows paths.
    此函数结合了对POSIX和Windows路径的检查。

    Args:
        string: The string to check.
               要检查的字符串。

    Returns:
        bool: True if the string looks like a filesystem path, False otherwise.
              如果字符串看起来像文件系统路径，则为True，否则为False。
    """
    return _is_posix_path(string) or _is_windows_path(string)


def guess_scheme(url):
    """
    Add an appropriate URL scheme if missing from the input.
    如果输入中缺少适当的URL协议，则添加它。

    This function examines the input and adds an appropriate scheme:
    - 'file://' for filesystem paths (both POSIX and Windows)
    - 'http://' for other inputs that look like URLs
    此函数检查输入并添加适当的协议：
    - 对于文件系统路径（POSIX和Windows），添加'file://'
    - 对于看起来像URL的其他输入，添加'http://'

    Args:
        url: The URL or path to process.
             要处理的URL或路径。

    Returns:
        str: The URL with an appropriate scheme added if it was missing.
             添加了适当协议（如果缺少）的URL。

    Note:
        This function uses any_to_uri() from w3lib.url to convert filesystem
        paths to proper file:// URLs.
        此函数使用w3lib.url中的any_to_uri()将文件系统路径转换为适当的file://URL。
    """
    # If it looks like a filesystem path, convert it to a file:// URL
    # 如果它看起来像文件系统路径，将其转换为file://URL
    if _is_filesystem_path(url):
        return any_to_uri(url)
    # Otherwise, add http:// if needed
    # 否则，如果需要，添加http://
    return add_http_if_no_scheme(url)


def strip_url(url, strip_credentials=True, strip_default_port=True, origin_only=False, strip_fragment=True):
    """
    Strip a URL string of some of its components.
    从URL字符串中去除某些组件。

    This function allows selectively removing parts of a URL, such as credentials,
    default ports, paths, queries, and fragments. It's useful for normalizing URLs
    or removing sensitive information.
    此函数允许选择性地移除URL的部分内容，如凭据、默认端口、路径、查询和片段。
    它对于规范化URL或移除敏感信息很有用。

    Args:
        url: The URL to strip.
             要处理的URL。
        strip_credentials: Whether to remove "user:password@" from the URL.
                          是否从URL中移除"user:password@"。
                          Defaults to True.
                          默认为True。
        strip_default_port: Whether to remove default ports (":80" for http,
                           ":443" for https, ":21" for ftp) from the URL.
                           是否从URL中移除默认端口（http的":80"，
                           https的":443"，ftp的":21"）。
                           Defaults to True.
                           默认为True。
        origin_only: Whether to keep only the origin part of the URL (scheme and netloc),
                    replacing the path with "/" and removing params, query, and fragment.
                    是否只保留URL的源部分（协议和网络位置），
                    将路径替换为"/"并移除参数、查询和片段。
                    This also implies strip_credentials=True.
                    这也意味着strip_credentials=True。
                    Defaults to False.
                    默认为False。
        strip_fragment: Whether to remove any #fragment component from the URL.
                       是否从URL中移除任何#片段组件。
                       Defaults to True.
                       默认为True。

    Returns:
        str: The stripped URL.
             处理后的URL。

    Examples:
        >>> strip_url("http://user:pass@example.com:80/path?query#fragment")
        'http://example.com/path?query'
        >>> strip_url("http://user:pass@example.com:80/path?query#fragment",
        ...           strip_credentials=False, strip_fragment=False)
        'http://user:pass@example.com/path?query#fragment'
        >>> strip_url("http://user:pass@example.com:80/path?query#fragment",
        ...           origin_only=True)
        'http://example.com/'
    """
    # Parse the URL into its components
    # 将URL解析为其组件
    parsed_url = urlparse(url)
    netloc = parsed_url.netloc

    # Remove credentials if requested or if origin_only is True
    # 如果请求或如果origin_only为True，则移除凭据
    if (strip_credentials or origin_only) and (parsed_url.username or parsed_url.password):
        netloc = netloc.split('@')[-1]

    # Remove default ports if requested
    # 如果请求，则移除默认端口
    if strip_default_port and parsed_url.port:
        if (parsed_url.scheme, parsed_url.port) in (('http', 80),
                                                    ('https', 443),
                                                    ('ftp', 21)):
            netloc = netloc.replace(f':{parsed_url.port}', '')

    # Reconstruct the URL with the desired components
    # 使用所需组件重建URL
    return urlunparse((
        parsed_url.scheme,
        netloc,
        '/' if origin_only else parsed_url.path,
        '' if origin_only else parsed_url.params,
        '' if origin_only else parsed_url.query,
        '' if strip_fragment else parsed_url.fragment
    ))
