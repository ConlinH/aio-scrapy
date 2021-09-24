import os

from setuptools import setup


def list_dir(dir):
    result = [dir]
    for file in os.listdir(dir):
        if os.path.isdir(os.path.join(dir, file)):
            result.extend(list_dir(os.path.join(dir, file)))
    return result


NAME = "aioscrapy"
PACKAGES = list_dir('aioscrapy')
DESCRIPTION = "aioscrapy"
LONG_DESCRIPTION = '将scrapy改写成asyncio版本'
URL = "https://github.com/conlin-huang/aioscrapy.git"
AUTHOR = "conlin"
AUTHOR_EMAIL = "995018884@qq.com"
VERSION = "1.0.0"
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
    ]
)
