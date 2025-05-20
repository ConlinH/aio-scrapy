"""
Excel Pipeline for AioScrapy
AioScrapy的Excel管道

This module provides a pipeline for storing scraped items in Excel files.
It includes a mixin class for Excel file handling and a pipeline class that
uses the mixin to process items and save them to Excel files. It supports
formatting dates and embedding images.
此模块提供了一个用于将抓取的项目存储在Excel文件中的管道。
它包括一个用于Excel文件处理的混入类和一个使用该混入类处理项目并将其保存到Excel文件的管道类。
它支持格式化日期和嵌入图像。
"""

import asyncio
import math
from io import BytesIO
from typing import Tuple, Optional

import requests
import xlsxwriter
from PIL import Image, ImageFile

from aioscrapy.utils.log import logger

try:
    # Use LANCZOS resampling filter for PIL 9.1.0 and above
    # 对PIL 9.1.0及以上版本使用LANCZOS重采样过滤器
    resample = Image.LANCZOS
except:
    # Fall back to ANTIALIAS for older PIL versions
    # 对较旧的PIL版本回退到ANTIALIAS
    resample = Image.ANTIALIAS
# Allow loading truncated images
# 允许加载截断的图像
ImageFile.LOAD_TRUNCATED_IMAGES = True


class ExcelSinkMixin:
    """
    Mixin class for Excel file handling.
    Excel文件处理的混入类。

    This mixin provides methods for saving items to Excel files, managing Excel workbooks
    and worksheets, and handling special data types like dates and images. It can be used
    by any class that needs to write data to Excel files.
    此混入类提供了将项目保存到Excel文件、管理Excel工作簿和工作表以及处理日期和图像等
    特殊数据类型的方法。它可以被任何需要将数据写入Excel文件的类使用。
    """
    # Dictionary to store worksheet objects by filename+sheet
    # 按文件名+工作表存储工作表对象的字典
    ws_cache = {}

    # Dictionary to store workbook objects by filename
    # 按文件名存储工作簿对象的字典
    wb_cache = {}

    # Dictionary to store field lists by filename+sheet
    # 按文件名+工作表存储字段列表的字典
    fields_cache = {}

    # Dictionary to store current row positions by filename+sheet
    # 按文件名+工作表存储当前行位置的字典
    y_cache = {}

    @staticmethod
    async def deal_img(url: str, img_size: Optional[Tuple[int, int]]) -> Optional[BytesIO]:
        """
        Download and process an image from a URL.
        从URL下载并处理图像。

        This method downloads an image from the given URL, optionally resizes it
        to the specified dimensions while maintaining aspect ratio, and returns
        it as a BytesIO object that can be embedded in an Excel file.
        此方法从给定的URL下载图像，可选择将其调整为指定的尺寸（同时保持纵横比），
        并将其作为可嵌入Excel文件的BytesIO对象返回。

        Args:
            url: The URL of the image to download.
                要下载的图像的URL。
            img_size: Optional tuple of (width, height) to resize the image to.
                     可选的(宽度, 高度)元组，用于调整图像大小。
                     If provided, the image will be resized to fit within these dimensions
                     while maintaining aspect ratio.
                     如果提供，图像将被调整大小以适应这些尺寸，同时保持纵横比。

        Returns:
            BytesIO: A BytesIO object containing the processed image,
                    or None if the image could not be downloaded or processed.
                    包含处理后图像的BytesIO对象，
                    如果无法下载或处理图像，则为None。
        """
        # Add https: prefix if URL starts with //
        # 如果URL以//开头，则添加https:前缀
        if url.startswith('//'):
            url = 'https:' + url

        # Download the image
        # 下载图像
        try:
            img_bytes = requests.get(url).content
        except Exception as e:
            logger.error(f"download img error: {e}")
            return None

        # Open the image using PIL
        # 使用PIL打开图像
        im = Image.open(BytesIO(img_bytes))
        im_format = im.format

        # Resize the image if a size is specified
        # 如果指定了大小，则调整图像大小
        if img_size:
            # Calculate scaling factor to maintain aspect ratio
            # 计算缩放因子以保持纵横比
            temp = max(im.size[0] / img_size[0], im.size[1] / img_size[1])
            img_size = (math.ceil(im.size[0] / temp), math.ceil(im.size[1] / temp))

            # Resize and convert to palette mode to reduce file size
            # 调整大小并转换为调色板模式以减小文件大小
            im = im.resize(img_size, resample).convert('P')

        # Save the processed image to a BytesIO object
        # 将处理后的图像保存到BytesIO对象
        result = BytesIO()
        im.save(result, format=im_format)

        # Reset the position to the beginning of the BytesIO object
        # 将位置重置到BytesIO对象的开头
        result.seek(0)

        return result

    async def save_item(
            self,
            item: dict,
            *,
            filename: Optional[str] = None,
            date_fields: Optional[list] = None,
            date_format: str = 'yyyy-mm-dd HH:MM:SS',
            img_fields: Optional[list] = None,
            img_size: Optional[Tuple[int, int]] = None,
            **options
    ):
        """
        Save an item to an Excel file.
        将项目保存到Excel文件。

        This method writes a dictionary item as a row in an Excel file. It handles
        special formatting for date fields and can embed images from URLs. The first row
        of the Excel file will contain the keys of the first item saved to the file.
        此方法将字典项目作为Excel文件中的一行写入。它处理日期字段的特殊格式，
        并可以嵌入来自URL的图像。Excel文件的第一行将包含保存到文件的第一个项目的键。

        Args:
            item: The dictionary item to save.
                 要保存的字典项目。
            filename: The name of the Excel file to save to.
                     要保存到的Excel文件的名称。
                     If not provided, an assertion error will be raised.
                     如果未提供，将引发断言错误。
            date_fields: Optional list of field names that should be formatted as dates.
                        应格式化为日期的字段名称的可选列表。
            date_format: The Excel date format to use for date fields.
                        用于日期字段的Excel日期格式。
                        Defaults to 'yyyy-mm-dd HH:MM:SS'.
                        默认为'yyyy-mm-dd HH:MM:SS'。
            img_fields: Optional list of field names that contain image URLs.
                       包含图像URL的字段名称的可选列表。
            img_size: Optional tuple of (width, height) to resize images to.
                     用于调整图像大小的可选(宽度, 高度)元组。
            **options: Additional options to pass to the Excel workbook.
                      传递给Excel工作簿的其他选项。

        Raises:
            AssertionError: If filename is None.
                           如果filename为None。
            Exception: If there is an error writing to the Excel file.
                      如果写入Excel文件时出错。
        """
        # Ensure filename is provided
        # 确保提供了文件名
        assert filename is not None, "请传入filename参数"

        # Add .xlsx extension if not present
        # 如果不存在，则添加.xlsx扩展名
        if '.xlsx' not in filename:
            filename = filename + '.xlsx'

        try:
            # Get or create workbook, worksheet, fields list, and current row
            # 获取或创建工作簿、工作表、字段列表和当前行
            wb, ws, fields, y = self._get_write_class(filename, item, **options)

            # Create cell formats for alternating row colors
            # 创建用于交替行颜色的单元格格式
            bold_format_1 = wb.add_format({'align': 'left', 'border': 1, 'valign': 'vcenter'})
            bold_format_2 = wb.add_format({'align': 'left', 'border': 1, 'valign': 'vcenter', 'fg_color': '#D0D3D4'})

            # Process each field in the item
            # 处理项目中的每个字段
            for x, field in enumerate(fields):
                # Alternate row colors
                # 交替行颜色
                if x % 2 == 0:
                    bold_format = bold_format_1
                else:
                    bold_format = bold_format_2

                # Handle date fields
                # 处理日期字段
                if date_fields is not None and field in date_fields:
                    ws.write_datetime(y, x, item.get(field), wb.add_format({'num_format': date_format}))

                # Handle image fields
                # 处理图像字段
                elif img_fields is not None and field in img_fields:
                    # Set column width if image size is specified
                    # 如果指定了图像大小，则设置列宽
                    img_size and ws.set_column_pixels(x, x, width=math.ceil(img_size[0]))

                    # Get image URL from item
                    # 从项目获取图像URL
                    url = item.get(field)

                    # Download and process the image
                    # 下载并处理图像
                    img_bytes = await self.deal_img(url, img_size)

                    # Insert the image or fall back to writing the URL if insertion fails
                    # 插入图像，如果插入失败，则回退到写入URL
                    if img_bytes is None or ws.insert_image(y, x, '', {'image_data': img_bytes}) == -1:
                        ws.write(y, x, url, bold_format)

                # Handle regular fields
                # 处理常规字段
                else:
                    ws.write(y, x, item.get(field), bold_format)

            # Set row and column dimensions if image size is specified
            # 如果指定了图像大小，则设置行和列尺寸
            if img_size is not None:
                ws.set_column_pixels(0, len(fields), width=math.ceil(img_size[0]))
                ws.set_row_pixels(y, height=math.ceil(img_size[1]))

        except Exception as e:
            # Log any errors that occur
            # 记录发生的任何错误
            logger.exception(f'Save Execl Error, filename:{filename}, item:{item}, errMsg: {e}')

    def _get_write_class(self, filename, item, sheet='sheet1', **options):
        """
        Get or create workbook, worksheet, fields list, and current row for a file.
        获取或创建文件的工作簿、工作表、字段列表和当前行。

        This method returns existing Excel objects for the given filename and sheet
        if they exist, or creates new ones if not. When creating a new worksheet,
        it also writes the header row using the keys of the provided item.
        如果存在，此方法返回给定文件名和工作表的现有Excel对象，如果不存在，则创建新的。
        创建新工作表时，它还使用提供的项目的键写入标题行。

        Args:
            filename: The name of the Excel file.
                     Excel文件的名称。
            item: The dictionary item whose keys will be used as headers.
                 其键将用作标题的字典项目。
            sheet: The name of the worksheet to use.
                  要使用的工作表的名称。
                  Defaults to 'sheet1'.
                  默认为'sheet1'。
            **options: Additional options to pass to the Excel workbook.
                      传递给Excel工作簿的其他选项。

        Returns:
            tuple: A tuple containing (workbook, worksheet, fields, row_number).
                  包含(工作簿, 工作表, 字段, 行号)的元组。
        """
        # Create a unique key for the worksheet cache
        # 为工作表缓存创建唯一键
        filename_sheet = filename + sheet

        # If this worksheet doesn't exist yet, create it
        # 如果此工作表尚不存在，则创建它
        if self.ws_cache.get(filename_sheet) is None:
            # If the workbook doesn't exist yet, create it
            # 如果工作簿尚不存在，则创建它
            if self.wb_cache.get(filename) is None:
                logger.info(f'Create Execl: {filename}')
                wb = xlsxwriter.Workbook(filename, options=options)
                self.wb_cache[filename] = wb
            else:
                wb = self.wb_cache[filename]

            # Create a new worksheet
            # 创建新工作表
            ws = wb.add_worksheet(sheet)

            # Create a format for the header row
            # 为标题行创建格式
            bold_format = wb.add_format(
                {'bold': True, 'font_size': 12, 'border': 1, 'align': 'center', 'valign': 'vcenter'})

            # Get the field names from the item
            # 从项目获取字段名称
            fields = list(item.keys())

            # Write the header row
            # 写入标题行
            ws.write_row('A1', fields, cell_format=bold_format)
            ws.set_row(0, height=30)

            # Store the worksheet, fields, and row counter in the caches
            # 将工作表、字段和行计数器存储在缓存中
            self.fields_cache[filename_sheet] = fields
            self.ws_cache[filename_sheet] = ws
            self.y_cache[filename_sheet] = 0

        # Increment the row counter for this worksheet
        # 增加此工作表的行计数器
        self.y_cache[filename_sheet] += 1

        # Return the workbook, worksheet, fields, and current row
        # 返回工作簿、工作表、字段和当前行
        return self.wb_cache[filename], \
            self.ws_cache[filename_sheet], \
            self.fields_cache[filename_sheet], \
            self.y_cache[filename_sheet]

    def close_execl(self, filename=None):
        """
        Close a specific Excel file.
        关闭特定的Excel文件。

        This method closes the workbook for a specific Excel file and removes
        all related objects from the caches.
        此方法关闭特定Excel文件的工作簿，并从缓存中删除所有相关对象。

        Args:
            filename: The name of the Excel file to close.
                     要关闭的Excel文件的名称。
                     If None or not found in the cache, nothing happens.
                     如果为None或在缓存中未找到，则不会发生任何事情。
        """
        # If the filename is not in the cache, return
        # 如果文件名不在缓存中，则返回
        if filename not in self.wb_cache:
            return

        # Log that we're closing the file
        # 记录我们正在关闭文件
        logger.info(f'Closing Execl: {filename}')

        # Close the workbook if it exists
        # 如果工作簿存在，则关闭它
        if wb := self.wb_cache.pop(filename):
            wb.close()

        # Remove all worksheets, row counters, and fields lists for this file
        # 删除此文件的所有工作表、行计数器和字段列表
        for filename_sheet in list(self.ws_cache.keys()):
            if not filename_sheet.startswith(filename):
                continue
            self.ws_cache.pop(filename_sheet, None)
            self.y_cache.pop(filename_sheet, None)
            self.fields_cache.pop(filename_sheet, None)

    def close(self):
        """
        Close all open Excel files.
        关闭所有打开的Excel文件。

        This method closes all workbooks for all Excel files that have been
        opened by this instance.
        此方法关闭此实例打开的所有Excel文件的所有工作簿。
        """
        # Make a copy of the keys to avoid modifying the dictionary during iteration
        # 复制键以避免在迭代期间修改字典
        for filename in list(self.wb_cache.keys()):
            self.close_execl(filename)


class ExcelPipeline(ExcelSinkMixin):
    """
    Pipeline for storing scraped items in Excel files.
    用于将抓取的项目存储在Excel文件中的管道。

    This pipeline uses the ExeclSinkMixin to save items to Excel files. It processes
    items that have a '__execl__' key, which contains parameters for the Excel file
    such as the filename, sheet name, and image settings.
    此管道使用ExeclSinkMixin将项目保存到Excel文件中。它处理具有'__execl__'键的项目，
    该键包含Excel文件的参数，如文件名、工作表名称和图像设置。

    Note: The class name is misspelled as "Execl" instead of "Excel" for backward compatibility.
    注意：类名拼写为"Execl"而不是"Excel"，以保持向后兼容性。
    """

    def __init__(self, settings):
        """
        Initialize the Excel pipeline.
        初始化Excel管道。

        Args:
            settings: The AioScrapy settings object.
                     AioScrapy设置对象。
                     Not used in the current implementation, but included for
                     compatibility with the pipeline interface.
                     在当前实现中未使用，但为了与管道接口兼容而包含。
        """
        # Create a lock to ensure thread-safe access to Excel files
        # 创建锁以确保对Excel文件的线程安全访问
        self.lock = asyncio.Lock()

    @classmethod
    def from_settings(cls, settings):
        """
        Create an ExeclPipeline instance from settings.
        从设置创建ExeclPipeline实例。

        This is the factory method used by AioScrapy to create pipeline instances.
        这是AioScrapy用于创建管道实例的工厂方法。

        Args:
            settings: The AioScrapy settings object.
                     AioScrapy设置对象。

        Returns:
            ExeclPipeline: A new ExeclPipeline instance.
                          一个新的ExeclPipeline实例。
        """
        return cls(settings)

    async def process_item(self, item, spider):
        """
        Process an item and save it to an Excel file if it has a '__execl__' key.
        处理项目，如果它有'__execl__'键，则将其保存到Excel文件。

        This method checks if the item has a '__execl__' key. If it does, it uses
        the parameters in that key to save the item to an Excel file. If not, it
        logs a warning and returns the item unchanged.
        此方法检查项目是否具有'__execl__'键。如果有，它使用该键中的参数将项目
        保存到Excel文件。如果没有，它会记录警告并返回未更改的项目。

        Args:
            item: The item to process.
                 要处理的项目。
            spider: The spider that generated the item.
                   生成项目的爬虫。

        Returns:
            dict: The processed item.
                 处理后的项目。
        """
        # Extract Excel parameters from the item
        # 从项目中提取Excel参数
        execl_kw: Optional[dict] = item.pop('__execl__', None)

        # If no Excel parameters, log a warning and return the item
        # 如果没有Excel参数，记录警告并返回项目
        if not execl_kw:
            logger.warning(f"item Missing key __execl__, not stored")
            return item

        # Use the spider name as the default filename
        # 使用爬虫名称作为默认文件名
        execl_kw.setdefault('filename', spider.name)

        # Use a lock to ensure thread-safe access to Excel files
        # 使用锁确保对Excel文件的线程安全访问
        async with self.lock:
            # Save the item to an Excel file
            # 将项目保存到Excel文件
            await self.save_item(item, **execl_kw)

        return item

    async def close_spider(self, spider):
        """
        Close all open Excel files when the spider is closed.
        当爬虫关闭时关闭所有打开的Excel文件。

        This method is called by AioScrapy when a spider is closed. It ensures
        that all Excel files opened by this pipeline are properly closed.
        当爬虫关闭时，AioScrapy调用此方法。它确保此管道打开的所有Excel文件
        都正确关闭。

        Args:
            spider: The spider that was closed.
                   被关闭的爬虫。
        """
        # Close all open Excel files
        # 关闭所有打开的Excel文件
        self.close()


# Test code for the Excel pipeline
# Excel管道的测试代码
if __name__ == '__main__':
    """
    Test code to demonstrate the usage of the ExeclPipeline.
    演示ExeclPipeline用法的测试代码。

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
        Async test function to demonstrate the ExeclPipeline.
        演示ExeclPipeline的异步测试函数。
        """
        # Create a new Excel pipeline
        # 创建一个新的Excel管道
        p = ExcelPipeline({})

        # Process a test item with Excel parameters
        # 处理带有Excel参数的测试项目
        await p.process_item({
            'title': 'tttt',
            'img': '//www.baidu.com/img/flexible/logo/pc/result.png',
            '__execl__': {
                'sheet': 'sheet1',
                # Uncomment these lines to test additional features
                # 取消注释这些行以测试其他功能
                # 'filename': 'test',
                # 'img_fields': ['img'],
                # 'img_size': (100, 500)
            }
        }, TestSpider())

        # Close the pipeline
        # 关闭管道
        await p.close_spider(None)


    # Run the test function
    # 运行测试函数
    asyncio.run(test())
