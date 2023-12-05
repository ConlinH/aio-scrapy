# Define your item pipelines here
from aioscrapy import logger


class DemoPipeline:
    def process_item(self, item, spider):
        logger.info(f"From DemoPipeline: {item}")
        return item
