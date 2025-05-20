"""
CSV Pipeline for AioScrapy
AioScrapy的CSV管道

This module provides a pipeline for storing scraped items in CSV files.
It includes a mixin class for CSV file handling and a pipeline class that
uses the mixin to process items and save them to CSV files.
此模块提供了一个用于将抓取的项目存储在CSV文件中的管道。
它包括一个用于CSV文件处理的混入类和一个使用该混入类处理项目并将其保存到CSV文件的管道类。
"""

import asyncio
import csv
from typing import Optional

from aioscrapy.utils.log import logger


class CsvSinkMixin:
    """
    Mixin class for CSV file handling.
    CSV文件处理的混入类。

    This mixin provides methods for saving items to CSV files, managing CSV writers,
    and closing CSV files. It can be used by any class that needs to write data to
    CSV files.
    此混入类提供了将项目保存到CSV文件、管理CSV写入器和关闭CSV文件的方法。
    它可以被任何需要将数据写入CSV文件的类使用。
    """

    # Dictionary to store CSV writers and file handles, keyed by filename
    # 用于存储CSV写入器和文件句柄的字典，以文件名为键
    csv_writer = {}

    async def save_item(
            self,
            item: dict,
            *,
            filename: Optional[str] = None,
    ):
        """
        Save an item to a CSV file.
        将项目保存到CSV文件。

        This method writes a dictionary item as a row in a CSV file. The first row
        of the CSV file will contain the keys of the first item saved to the file.
        此方法将字典项目作为CSV文件中的一行写入。CSV文件的第一行将包含保存到
        文件的第一个项目的键。

        Args:
            item: The dictionary item to save.
                 要保存的字典项目。
            filename: The name of the CSV file to save to.
                     要保存到的CSV文件的名称。
                     If not provided, an assertion error will be raised.
                     如果未提供，将引发断言错误。

        Raises:
            AssertionError: If filename is None.
                           如果filename为None。
            Exception: If there is an error writing to the CSV file.
                      如果写入CSV文件时出错。
        """
        # Ensure filename is provided
        # 确保提供了文件名
        assert filename is not None, "请传入filename参数"

        # Add .csv extension if not present
        # 如果不存在，则添加.csv扩展名
        if '.csv' not in filename:
            filename = filename + '.csv'

        try:
            # Get or create a CSV writer for this file
            # 获取或创建此文件的CSV写入器
            writer = self._get_writer(filename, item)

            # Write the item values as a row
            # 将项目值作为一行写入
            writer.writerow(item.values())
        except Exception as e:
            # Log any errors that occur
            # 记录发生的任何错误
            logger.exception(f'Save csv Error, filename:{filename}, item:{item}, errMsg: {e}')

    def _get_writer(self, filename, item):
        """
        Get or create a CSV writer for a file.
        获取或创建文件的CSV写入器。

        This method returns an existing CSV writer for the given filename if one
        exists, or creates a new one if not. When creating a new writer, it also
        writes the header row using the keys of the provided item.
        如果存在，此方法返回给定文件名的现有CSV写入器，如果不存在，则创建一个新的。
        创建新写入器时，它还使用提供的项目的键写入标题行。

        Args:
            filename: The name of the CSV file.
                     CSV文件的名称。
            item: The dictionary item whose keys will be used as headers.
                 其键将用作标题的字典项目。

        Returns:
            csv.writer: A CSV writer object for the file.
                       文件的CSV写入器对象。
        """
        # Try to get an existing writer
        # 尝试获取现有的写入器
        writer, *_ = self.csv_writer.get(filename, (None, None))

        # If no writer exists, create a new one
        # 如果不存在写入器，则创建一个新的
        if writer is None:
            # Open the file for writing
            # 打开文件进行写入
            file = open(filename, 'w', encoding="UTF8", newline='')

            # Create a CSV writer
            # 创建CSV写入器
            writer = csv.writer(file)

            # Write the header row using the item keys
            # 使用项目键写入标题行
            writer.writerow(item.keys())

            # Store the writer and file handle
            # 存储写入器和文件句柄
            self.csv_writer[filename] = (writer, file)

        return writer

    def close_csv(self, filename=None):
        """
        Close a specific CSV file.
        关闭特定的CSV文件。

        This method closes the file handle for a specific CSV file and removes
        its writer from the csv_writer dictionary.
        此方法关闭特定CSV文件的文件句柄，并从csv_writer字典中删除其写入器。

        Args:
            filename: The name of the CSV file to close.
                     要关闭的CSV文件的名称。
                     If None, nothing happens.
                     如果为None，则不会发生任何事情。
        """
        # Remove the writer and file handle from the dictionary
        # 从字典中删除写入器和文件句柄
        *_, file = self.csv_writer.pop(filename, (None, None))

        # If a file handle was found, close it
        # 如果找到文件句柄，则关闭它
        if file is not None:
            logger.info(f'Closing csv: {filename}')
            file.close()

    def close(self):
        """
        Close all open CSV files.
        关闭所有打开的CSV文件。

        This method closes all file handles for all CSV files that have been
        opened by this instance.
        此方法关闭此实例打开的所有CSV文件的所有文件句柄。
        """
        # Make a copy of the keys to avoid modifying the dictionary during iteration
        # 复制键以避免在迭代期间修改字典
        for filename in list(self.csv_writer.keys()):
            self.close_csv(filename)


class CsvPipeline(CsvSinkMixin):
    """
    Pipeline for storing scraped items in CSV files.
    用于将抓取的项目存储在CSV文件中的管道。

    This pipeline uses the CsvSinkMixin to save items to CSV files. It processes
    items that have a '__csv__' key, which contains parameters for the CSV file
    such as the filename.
    此管道使用CsvSinkMixin将项目保存到CSV文件中。它处理具有'__csv__'键的项目，
    该键包含CSV文件的参数，如文件名。
    """

    def __init__(self, settings):
        """
        Initialize the CSV pipeline.
        初始化CSV管道。

        Args:
            settings: The AioScrapy settings object.
                     AioScrapy设置对象。
                     Not used in the current implementation, but included for
                     compatibility with the pipeline interface.
                     在当前实现中未使用，但为了与管道接口兼容而包含。
        """
        # Create a lock to ensure thread-safe access to CSV files
        # 创建锁以确保对CSV文件的线程安全访问
        self.lock = asyncio.Lock()

    @classmethod
    def from_settings(cls, settings):
        """
        Create a CsvPipeline instance from settings.
        从设置创建CsvPipeline实例。

        This is the factory method used by AioScrapy to create pipeline instances.
        这是AioScrapy用于创建管道实例的工厂方法。

        Args:
            settings: The AioScrapy settings object.
                     AioScrapy设置对象。

        Returns:
            CsvPipeline: A new CsvPipeline instance.
                        一个新的CsvPipeline实例。
        """
        return cls(settings)

    async def process_item(self, item, spider):
        """
        Process an item and save it to a CSV file if it has a '__csv__' key.
        处理项目，如果它有'__csv__'键，则将其保存到CSV文件。

        This method checks if the item has a '__csv__' key. If it does, it uses
        the parameters in that key to save the item to a CSV file. If not, it
        logs a warning and returns the item unchanged.
        此方法检查项目是否具有'__csv__'键。如果有，它使用该键中的参数将项目
        保存到CSV文件。如果没有，它会记录警告并返回未更改的项目。

        Args:
            item: The item to process.
                 要处理的项目。
            spider: The spider that generated the item.
                   生成项目的爬虫。

        Returns:
            dict: The processed item.
                 处理后的项目。
        """
        # Extract CSV parameters from the item
        # 从项目中提取CSV参数
        execl_kw: Optional[dict] = item.pop('__csv__', None)

        # If no CSV parameters, log a warning and return the item
        # 如果没有CSV参数，记录警告并返回项目
        if not execl_kw:
            logger.warning(f"item Missing key __csv__, not stored")
            return item

        # Use the spider name as the default filename
        # 使用爬虫名称作为默认文件名
        execl_kw.setdefault('filename', spider.name)

        # Use a lock to ensure thread-safe access to CSV files
        # 使用锁确保对CSV文件的线程安全访问
        async with self.lock:
            # Save the item to a CSV file
            # 将项目保存到CSV文件
            await self.save_item(item, **execl_kw)

        return item

    async def close_spider(self, spider):
        """
        Close all open CSV files when the spider is closed.
        当爬虫关闭时关闭所有打开的CSV文件。

        This method is called by AioScrapy when a spider is closed. It ensures
        that all CSV files opened by this pipeline are properly closed.
        当爬虫关闭时，AioScrapy调用此方法。它确保此管道打开的所有CSV文件
        都正确关闭。

        Args:
            spider: The spider that was closed.
                   被关闭的爬虫。
        """
        # Close all open CSV files
        # 关闭所有打开的CSV文件
        self.close()


# Test code for the CSV pipeline
# CSV管道的测试代码
if __name__ == '__main__':
    """
    Test code to demonstrate the usage of the CsvPipeline.
    演示CsvPipeline用法的测试代码。

    This code creates a simple test spider and pipeline, processes a test item,
    and then closes the pipeline.
    此代码创建一个简单的测试爬虫和管道，处理一个测试项目，然后关闭管道。
    """

    class TestSpider:
        """
        Simple test spider class with a name attribute.
        具有name属性的简单测试爬虫类。
        """
        name = 'TestSpider'


    async def test():
        """
        Async test function to demonstrate the CsvPipeline.
        演示CsvPipeline的异步测试函数。
        """
        # Create a new CSV pipeline
        # 创建一个新的CSV管道
        p = CsvPipeline({})

        # Process a test item with CSV parameters
        # 处理带有CSV参数的测试项目
        await p.process_item({
            'title': '测试',
            'img': '//www.baidu.com/img/flexible/logo/pc/result.png',
            '__csv__': {
                'filename': 'test',
            }
        }, TestSpider())

        # Close the pipeline
        # 关闭管道
        await p.close_spider(None)


    # Run the test function
    # 运行测试函数
    asyncio.run(test())
