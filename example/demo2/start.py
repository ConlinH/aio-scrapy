import sys
import os
sys.path.append(os.path.dirname(os.getcwd()) + '/aioscrapy')

from aioscrapy.utils.tools import get_project_settings
from aioscrapy.crawler import CrawlerProcess
# from baiduSpider import BaiduSpider
# from baidu2Spider import Baidu2Spider
# from baidu3Spider import Baidu3Spider


settings = get_project_settings()
cp = CrawlerProcess(settings)
# cp.crawl(BaiduSpider)
# cp.crawl(Baidu2Spider)
cp.crawl("Baidu3Spider")
cp.start()

#
# import asyncio
# import sys
# import os
# import signal
#
#
# sys.path.append(os.path.dirname(os.getcwd()) + '/aioscrapy')
#
#
# async def test():
#     print('vvvvvvvvvvvvvv')
#     print('vvvvvvvvvvvvvv')
#     print('vvvvvvvvvvvvvv')
#     await asyncio.sleep(10)
#     print('nnnnnnnnnnnnnnn')
#     print('nnnnnnnnnnnnnnn')
#     print('nnnnnnnnnnnnnnn')
#     print('nnnnnnnnnnnnnnn')
#
#
# async def get_date():
#     task = asyncio.create_task(test())
#     code = "from example.baidu3Spider import Baidu3Spider; Baidu3Spider.start()"
#     print(f"{sys.executable} -c '{code}'")
#
#     # Create the subprocess; redirect the standard output
#     # into a pipe.
#     proc = await asyncio.create_subprocess_exec(sys.executable, '-c', code)
#     # proc = await asyncio.create_subprocess_shell(f'{sys.executable} -c "{code}"')
#         # stdout=asyncio.subprocess.PIPE)
#
#     # proc2 = await asyncio.create_subprocess_exec(
#     #     sys.executable, '-c', code)
#     # Read one line of output.
#     # data = await proc.stdout.readline()
#     # line = data.decode('ascii').rstrip()
#
#     # Wait for the subprocess exit.
#     print(11111111111111111)
#     await asyncio.sleep(3)
#     # print(22222222222)
#     proc.send_signal(signal.SIGTERM)
#
#     # proc.send_signal(signal.CTRL_C_EVENT)
#     await task
#     # print(22222222222)
#     # print(33333333333333)
#     # proc.terminate()
#     # # proc.send_signal(signal.SIGINT)
#     #
#     # print(22222222222)
#     await asyncio.sleep(3)
#     # # proc2.send_signal(signal.CTRL_C_EVENT)
#     # # print(33333333333333)
#     # await proc.wait()
#     # print(444444444444444444)
#     # await asyncio.sleep(3)
#     # return line
#     # await proc.wait()
#
#
# if sys.platform == "win32":
#     asyncio.set_event_loop_policy(
#         asyncio.WindowsProactorEventLoopPolicy())
#
# asyncio.run(get_date(), debug=True)
# print(f"ggggggggggggggggg")
# print(f"ggggggggggggggggg")
# print(f"ggggggggggggggggg")
# print(f"ggggggggggggggggg")


