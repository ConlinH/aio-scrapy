# 安装指南 | Installation Guide

本页面提供了安装AioScrapy的详细说明。</br>
This page provides detailed instructions for installing AioScrapy.

## 系统要求 | System Requirements

AioScrapy支持以下操作系统：</br>
AioScrapy supports the following operating systems:

- Windows
- Linux
- macOS

## Python版本 | Python Version

AioScrapy需要Python 3.9或更高版本。</br>
AioScrapy requires Python 3.9 or higher.

您可以使用以下命令检查您的Python版本：</br>
You can check your Python version with the following command:

```bash
python --version
```

## 安装方法 | Installation Methods
### 使用pip安装 | Install with pip

推荐使用pip安装AioScrapy：</br>
It is recommended to install AioScrapy using pip:

```bash
pip install aio-scrapy
```

### 安装可选依赖 | Install Optional Dependencies

AioScrapy提供了多个可选依赖包，以支持不同的功能：</br>
AioScrapy provides several optional dependency packages to support different features:

```bash
# 安装所有可选依赖 | Install all optional dependencies
pip install aio-scrapy[all]

# 安装Redis支持 | Install Redis support
pip install aio-scrapy[redis]

# 安装MySQL支持 | Install MySQL support
pip install aio-scrapy[mysql]

# 安装MongoDB支持 | Install MongoDB support
pip install aio-scrapy[mongo]

# 安装PostgreSQL支持 | Install PostgreSQL support
pip install aio-scrapy[pg]

# 安装RabbitMQ支持 | Install RabbitMQ support
pip install aio-scrapy[rabbitmq]
```

### 从源代码安装 | Install from Source

您也可以从源代码安装AioScrapy：
You can also install AioScrapy from source:

```bash
git clone https://github.com/conlin-huang/aio-scrapy.git
cd aio-scrapy
pip install -e .
```

## 验证安装 | Verify Installation

安装完成后，您可以通过运行以下命令来验证安装是否成功：</br>
After installation, you can verify that the installation was successful by running the following command:

```bash
aioscrapy version
```

如果安装成功，您将看到AioScrapy的版本信息。</br>
If the installation was successful, you will see the AioScrapy version information.

## 安装不同的下载器 | Installing Different Downloaders

AioScrapy支持多种HTTP客户端作为下载器。默认使用aiohttp，但您可以安装其他客户端以使用不同的下载器：</br>
AioScrapy supports multiple HTTP clients as downloaders. It uses aiohttp by default, but you can install other clients to use different downloaders:

```bash
# 安装httpx支持 | Install httpx support
pip install httpx

# 安装playwright支持（用于JavaScript渲染） | Install playwright support (for JavaScript rendering)
pip install playwright
python -m playwright install

# 安装pyhttpx支持 | Install pyhttpx support
pip install pyhttpx

# 安装curl_cffi支持 | Install curl_cffi support
pip install curl_cffi

# 安装DrissionPage支持 | Install DrissionPage support
pip install DrissionPage
```

### 更新AioScrapy | Updating AioScrapy

要更新到最新版本的AioScrapy，请使用：</br>
To update to the latest version of AioScrapy, use:

```bash
pip install --upgrade aio-scrapy
```
