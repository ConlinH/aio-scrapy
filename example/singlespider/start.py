import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.getcwd())))
from aioscrapy.process import multi_process_run, single_process_run

from demo_queue_memory import DemoMemorySpider
from demo_request_httpx import DemoHttpxSpider
from demo_request_playwright import DemoPlaywrightSpider

if __name__ == '__main__':

    # # 单进程跑多爬虫
    # single_process_run(
    #     (DemoMemorySpider, None),
    #     (DemoHttpxSpider, None),
    #     # ...
    # )

    # 多进程跑多爬虫
    multi_process_run(
        [(DemoMemorySpider, None), (DemoHttpxSpider, None)],   # 子进程进程里面跑多爬虫
        (DemoPlaywrightSpider, None),     # 子进程进程里面跑但爬虫
        # ...
    )
