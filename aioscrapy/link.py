"""
Link Module
链接模块

This module defines the Link object used in Link extractors. The Link class
represents an extracted link from a web page, containing information such as
the URL, anchor text, URL fragment, and nofollow status.
此模块定义了链接提取器中使用的Link对象。Link类表示从网页中提取的链接，
包含URL、锚文本、URL片段和nofollow状态等信息。

For actual link extractors implementation see scrapy.linkextractors, or
its documentation in: docs/topics/link-extractors.rst
有关实际链接提取器的实现，请参见scrapy.linkextractors，
或其文档：docs/topics/link-extractors.rst
"""


class Link:
    """
    Represents an extracted link from a web page.
    表示从网页中提取的链接。

    Link objects are created by LinkExtractors to represent links extracted from web pages.
    Each Link object contains information about the URL, anchor text, URL fragment, and
    nofollow status of the extracted link.
    Link对象由LinkExtractor创建，用于表示从网页中提取的链接。每个Link对象包含有关
    提取链接的URL、锚文本、URL片段和nofollow状态的信息。

    Using the anchor tag sample below to illustrate the parameters::
    使用下面的锚标签示例来说明参数::

            <a href="https://example.com/nofollow.html#foo" rel="nofollow">Dont follow this one</a>

    Args:
        url: The absolute URL being linked to in the anchor tag.
             锚标签中链接到的绝对URL。
             From the sample, this is ``https://example.com/nofollow.html``.
             从示例中，这是``https://example.com/nofollow.html``。

        text: The text in the anchor tag.
              锚标签中的文本。
              From the sample, this is ``Dont follow this one``.
              从示例中，这是``Dont follow this one``。
              Defaults to an empty string.
              默认为空字符串。

        fragment: The part of the URL after the hash symbol.
                 URL中哈希符号后的部分。
                 From the sample, this is ``foo``.
                 从示例中，这是``foo``。
                 Defaults to an empty string.
                 默认为空字符串。

        nofollow: An indication of the presence or absence of a nofollow value
                 in the ``rel`` attribute of the anchor tag.
                 表示锚标签的``rel``属性中是否存在nofollow值。
                 Defaults to False.
                 默认为False。
    """

    # Define __slots__ to save memory when creating many Link objects
    # 定义__slots__以在创建多个Link对象时节省内存
    __slots__ = ['url', 'text', 'fragment', 'nofollow']

    def __init__(self, url, text='', fragment='', nofollow=False):
        """
        Initialize a Link object.
        初始化Link对象。

        Args:
            url: The absolute URL being linked to.
                 被链接到的绝对URL。
            text: The anchor text of the link.
                  链接的锚文本。
                  Defaults to an empty string.
                  默认为空字符串。
            fragment: The URL fragment (part after the # symbol).
                     URL片段（#符号后的部分）。
                     Defaults to an empty string.
                     默认为空字符串。
            nofollow: Whether the link has a nofollow attribute.
                     链接是否具有nofollow属性。
                     Defaults to False.
                     默认为False。

        Raises:
            TypeError: If the URL is not a string.
                      如果URL不是字符串。
        """
        # Ensure the URL is a string
        # 确保URL是字符串
        if not isinstance(url, str):
            got = url.__class__.__name__
            raise TypeError(f"Link urls must be str objects, got {got}")

        # Store the link attributes
        # 存储链接属性
        self.url = url
        self.text = text
        self.fragment = fragment
        self.nofollow = nofollow

    def __eq__(self, other):
        """
        Compare two Link objects for equality.
        比较两个Link对象是否相等。

        Two Link objects are considered equal if they have the same URL, text,
        fragment, and nofollow status.
        如果两个Link对象具有相同的URL、文本、片段和nofollow状态，则它们被认为是相等的。

        Args:
            other: The other Link object to compare with.
                  要比较的其他Link对象。

        Returns:
            bool: True if the Link objects are equal, False otherwise.
                 如果Link对象相等，则为True，否则为False。
        """
        return (
            self.url == other.url
            and self.text == other.text
            and self.fragment == other.fragment
            and self.nofollow == other.nofollow
        )

    def __hash__(self):
        """
        Calculate a hash value for the Link object.
        计算Link对象的哈希值。

        This method is implemented to allow Link objects to be used as dictionary
        keys or in sets. The hash value is based on the URL, text, fragment, and
        nofollow status.
        实现此方法是为了允许将Link对象用作字典键或集合中的元素。哈希值基于URL、
        文本、片段和nofollow状态。

        Returns:
            int: A hash value for the Link object.
                Link对象的哈希值。
        """
        return hash(self.url) ^ hash(self.text) ^ hash(self.fragment) ^ hash(self.nofollow)

    def __repr__(self):
        """
        Return a string representation of the Link object.
        返回Link对象的字符串表示。

        This method returns a string that, when passed to eval(), would create a
        new Link object with the same attributes.
        此方法返回一个字符串，当传递给eval()时，将创建一个具有相同属性的新Link对象。

        Returns:
            str: A string representation of the Link object.
                Link对象的字符串表示。
        """
        return (
            f'Link(url={self.url!r}, text={self.text!r}, '
            f'fragment={self.fragment!r}, nofollow={self.nofollow!r})'
        )
