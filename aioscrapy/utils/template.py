"""
Template utility functions for aioscrapy.
aioscrapy的模板实用函数。

This module provides utility functions for working with templates in aioscrapy.
It includes functions for rendering template files and string transformations
commonly used in code generation.
此模块提供了用于处理aioscrapy中模板的实用函数。
它包括用于渲染模板文件和在代码生成中常用的字符串转换的函数。
"""

import os
import re
import string


def render_templatefile(path, **kwargs):
    """
    Render a template file with the given parameters.
    使用给定参数渲染模板文件。

    This function reads a template file, substitutes variables using Python's
    string.Template, and writes the result back to the file system. If the file
    has a '.tmpl' extension, it will be renamed to remove this extension after
    rendering.
    此函数读取模板文件，使用Python的string.Template替换变量，
    并将结果写回文件系统。如果文件有'.tmpl'扩展名，
    渲染后将重命名以删除此扩展名。

    The template uses the syntax defined by string.Template, where variables are
    marked with a $ prefix (e.g., $variable or ${variable}).
    模板使用string.Template定义的语法，其中变量用$前缀标记
    （例如，$variable或${variable}）。

    Args:
        path: Path to the template file to render.
              要渲染的模板文件的路径。
        **kwargs: Variables to substitute in the template.
                 要在模板中替换的变量。

    Example:
        >>> render_templatefile('spider.py.tmpl',
        ...                     classname='MySpider',
        ...                     domain='example.com')

    Note:
        This function modifies the file system by:
        此函数通过以下方式修改文件系统：
        1. Potentially renaming the template file (if it ends with .tmpl)
           可能重命名模板文件（如果以.tmpl结尾）
        2. Writing the rendered content to the target file
           将渲染的内容写入目标文件
    """
    # Read the template file as UTF-8
    # 以UTF-8格式读取模板文件
    with open(path, 'rb') as fp:
        raw = fp.read().decode('utf8')

    # Substitute variables in the template
    # 替换模板中的变量
    content = string.Template(raw).substitute(**kwargs)

    # Determine the output path (remove .tmpl extension if present)
    # 确定输出路径（如果存在，则删除.tmpl扩展名）
    render_path = path[:-len('.tmpl')] if path.endswith('.tmpl') else path

    # Rename the file if it has a .tmpl extension
    # 如果文件有.tmpl扩展名，则重命名文件
    if path.endswith('.tmpl'):
        os.rename(path, render_path)

    # Write the rendered content back to the file
    # 将渲染的内容写回文件
    with open(render_path, 'wb') as fp:
        fp.write(content.encode('utf8'))


# Regular expression pattern to match characters that are not letters or digits
# Used by string_camelcase to remove invalid characters when converting to CamelCase
# 匹配非字母或数字的字符的正则表达式模式
# 由string_camelcase用于在转换为驼峰命名法时删除无效字符
CAMELCASE_INVALID_CHARS = re.compile(r'[^a-zA-Z\d]')


def string_camelcase(string):
    """
    Convert a string to CamelCase and remove invalid characters.
    将字符串转换为驼峰命名法并删除无效字符。

    This function converts a string to CamelCase by:
    1. Capitalizing the first letter of each word (using str.title())
    2. Removing all non-alphanumeric characters (using CAMELCASE_INVALID_CHARS regex)

    此函数通过以下方式将字符串转换为驼峰命名法：
    1. 将每个单词的首字母大写（使用str.title()）
    2. 删除所有非字母数字字符（使用CAMELCASE_INVALID_CHARS正则表达式）

    This is commonly used in code generation to convert variable names or
    identifiers from different formats (snake_case, kebab-case, etc.) to CamelCase.
    这在代码生成中常用于将变量名或标识符从不同格式
    （snake_case、kebab-case等）转换为驼峰命名法。

    Args:
        string: The input string to convert to CamelCase.
               要转换为驼峰命名法的输入字符串。

    Returns:
        str: The CamelCase version of the input string with invalid characters removed.
             输入字符串的驼峰命名法版本，已删除无效字符。

    Examples:
        >>> string_camelcase('lost-pound')
        'LostPound'

        >>> string_camelcase('missing_images')
        'MissingImages'

        >>> string_camelcase('hello world')
        'HelloWorld'
    """
    # Convert to title case (capitalize first letter of each word) and remove invalid chars
    # 转换为标题大小写（每个单词的首字母大写）并删除无效字符
    return CAMELCASE_INVALID_CHARS.sub('', string.title())
