import os

from setuptools import setup


def list_dir(dir_path):
    result = [dir_path]
    for file in os.listdir(dir_path):
        if os.path.isdir(os.path.join(dir_path, file)):
            result.extend(list_dir(os.path.join(dir_path, file)))
    return result


NAME = "aio_scrapy"
PACKAGES = list_dir('aioscrapy')
DESCRIPTION = "Replace twisted of Scrapy with asyncio and aiohttp"
LONG_DESCRIPTION = ''
URL = "https://github.com/conlin-huang/aio-scrapy.git"
AUTHOR = "conlin"
AUTHOR_EMAIL = "995018884@qq.com"
VERSION = "0.0.4"
LICENSE = "MIT"

setup(
    name=NAME,
    version=VERSION,
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.7',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
    ],
    url=URL,
    author=AUTHOR,
    author_email=AUTHOR_EMAIL,
    license=LICENSE,
    packages=PACKAGES,
    include_package_data=True,
    zip_safe=True,
    install_requires=[
        "scrapy-redis",
        "scrapy",
        "aiohttp",
        "aioredis >= 2.0.0",
        "aiomysql"
    ],
    keywords=[
        'aio-scrapy', 'scrapy', 'aioscrapy',
        'scrapy redis', 'asyncio', 'spider',
    ]
)
