import asyncio
import math
from io import BytesIO
from typing import Tuple, Optional

import requests
import xlsxwriter
from PIL import Image, ImageFile

from aioscrapy.utils.log import logger

try:
    resample = Image.LANCZOS
except:
    resample = Image.ANTIALIAS
ImageFile.LOAD_TRUNCATED_IMAGES = True


class ExeclSinkMixin:
    ws_cache = {}
    wb_cache = {}
    fields_cache = {}
    y_cache = {}

    @staticmethod
    async def deal_img(url: str, img_size: Optional[Tuple[int, int]]) -> Optional[BytesIO]:
        if url.startswith('//'):
            url = 'https:' + url
        try:
            img_bytes = requests.get(url).content
        except Exception as e:
            logger.error(f"download img error: {e}")
            return
        im = Image.open(BytesIO(img_bytes))
        im_format = im.format
        if img_size:
            temp = max(im.size[0] / img_size[0], im.size[1] / img_size[1])
            img_size = (math.ceil(im.size[0] / temp), math.ceil(im.size[1] / temp))
            im = im.resize(img_size, resample).convert('P')
        result = BytesIO()
        im.save(result, format=im_format)
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
        assert filename is not None, "请传入filename参数"
        if '.xlsx' not in filename:
            filename = filename + '.xlsx'
        try:
            wb, ws, fields, y = self._get_write_class(filename, item, **options)
            bold_format_1 = wb.add_format({'align': 'left', 'border': 1, 'valign': 'vcenter'})
            bold_format_2 = wb.add_format({'align': 'left', 'border': 1, 'valign': 'vcenter', 'fg_color': '#D0D3D4'})
            for x, field in enumerate(fields):
                if x % 2 == 0:
                    bold_format = bold_format_1
                else:
                    bold_format = bold_format_2
                if date_fields is not None and field in date_fields:
                    ws.write_datetime(y, x, item.get(field), wb.add_format({'num_format': date_format}))

                elif img_fields is not None and field in img_fields:
                    img_size and ws.set_column_pixels(x, x, width=math.ceil(img_size[0]))
                    url = item.get(field)
                    img_bytes = await self.deal_img(url, img_size)
                    if img_bytes is None or ws.insert_image(y, x, '', {'image_data': img_bytes}) == -1:
                        ws.write(y, x, url, bold_format)
                else:
                    ws.write(y, x, item.get(field), bold_format)
            if img_size is not None:
                ws.set_column_pixels(0, len(fields), width=math.ceil(img_size[0]))
                ws.set_row_pixels(y, height=math.ceil(img_size[1]))
        except Exception as e:
            logger.exception(f'Save Execl Error, filename:{filename}, item:{item}, errMsg: {e}')

    def _get_write_class(self, filename, item, sheet='sheet1', **options):
        filename_sheet = filename + sheet
        if self.ws_cache.get(filename_sheet) is None:
            if self.wb_cache.get(filename) is None:
                logger.info(f'Create Execl: {filename}')
                wb = xlsxwriter.Workbook(filename, options=options)
                self.wb_cache[filename] = wb
            else:
                wb = self.wb_cache[filename]
            ws = wb.add_worksheet(sheet)
            bold_format = wb.add_format(
                {'bold': True, 'font_size': 12, 'border': 1, 'align': 'center', 'valign': 'vcenter'})
            fields = list(item.keys())
            ws.write_row('A1', fields, cell_format=bold_format)
            ws.set_row(0, height=30)
            self.fields_cache[filename_sheet] = fields
            self.ws_cache[filename_sheet] = ws
            self.y_cache[filename_sheet] = 0
        self.y_cache[filename_sheet] += 1
        return self.wb_cache[filename], \
            self.ws_cache[filename_sheet], \
            self.fields_cache[filename_sheet], \
            self.y_cache[filename_sheet]

    def close_execl(self, filename=None):
        if filename not in self.wb_cache:
            return

        logger.info(f'Closing Execl: {filename}')
        if wb := self.wb_cache.pop(filename):
            wb.close()
        for filename_sheet in list(self.ws_cache.keys()):
            if not filename_sheet.startswith(filename):
                continue
            self.ws_cache.pop(filename_sheet, None)
            self.y_cache.pop(filename_sheet, None)
            self.fields_cache.pop(filename_sheet, None)

    def close(self):
        for filename in list(self.wb_cache.keys()):
            self.close_execl(filename)


class ExeclPipeline(ExeclSinkMixin):
    def __init__(self, settings):
        self.lock = asyncio.Lock()

    @classmethod
    def from_settings(cls, settings):
        return cls(settings)

    async def process_item(self, item, spider):
        execl_kw: Optional[dict] = item.pop('__execl__', None)
        if not execl_kw:
            logger.warning(f"item Missing key __execl__, not stored")
            return item

        execl_kw.setdefault('filename', spider.name)
        async with self.lock:
            await self.save_item(item, **execl_kw)

    async def close_spider(self, spider):
        self.close()


if __name__ == '__main__':
    class TestSpider:
        name = 'TestSpider'


    async def test():
        p = ExeclPipeline({})
        await p.process_item({
            'title': 'tttt',
            'img': '//www.baidu.com/img/flexible/logo/pc/result.png',
            '__execl__': {
                'sheet': 'sheet1',
                # 'filename': 'test',
                # 'img_fields': ['img'],
                # 'img_size': (100, 500)
            }
        }, TestSpider())
        await p.close_spider(None)


    asyncio.run(test())
