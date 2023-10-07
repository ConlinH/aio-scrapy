import asyncio
import csv
from typing import Optional

from aioscrapy.utils.log import logger


class CsvSinkMixin:
    csv_writer = {}

    async def save_item(
            self,
            item: dict,
            *,
            filename: Optional[str] = None,
    ):
        assert filename is not None, "请传入filename参数"
        if '.csv' not in filename:
            filename = filename + '.csv'
        try:
            writer = self._get_writer(filename, item)
            writer.writerow(item.values())
        except Exception as e:
            logger.exception(f'Save csv Error, filename:{filename}, item:{item}, errMsg: {e}')

    def _get_writer(self, filename, item):
        writer, *_ = self.csv_writer.get(filename, (None, None))
        if writer is None:
            file = open(filename, 'w', encoding="UTF8", newline='')
            writer = csv.writer(file)
            writer.writerow(item.keys())
            self.csv_writer[filename] = (writer, file)
        return writer

    def close_csv(self, filename=None):
        *_, file = self.csv_writer.pop(filename, (None, None))
        if file is not None:
            logger.info(f'Closing csv: {filename}')
            file.close()

    def close(self):
        for filename in list(self.csv_writer.keys()):
            self.close_csv(filename)


class CsvPipeline(CsvSinkMixin):
    def __init__(self, settings):
        self.lock = asyncio.Lock()

    @classmethod
    def from_settings(cls, settings):
        return cls(settings)

    async def process_item(self, item, spider):
        execl_kw: Optional[dict] = item.pop('__csv__', None)
        if not execl_kw:
            logger.warning(f"item Missing key __csv__, not stored")
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
        p = CsvPipeline({})
        await p.process_item({
            'title': '测试',
            'img': '//www.baidu.com/img/flexible/logo/pc/result.png',
            '__csv__': {
                'filename': 'test',
            }
        }, TestSpider())

        await p.close_spider(None)


    asyncio.run(test())
