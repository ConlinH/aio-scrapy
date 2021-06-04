# aioscrapy

将基于twisted的scrapy/scrapy-redis改成基于asyncio, 保留了几乎所有的scrapy/scrapy-reids功能

### 安装

``` 

# python版本>=3.7 (此项目是在3.8版本开发的)

# 下载
git clone https://github.com/conlin-huang/aioscrapy.git

# 安装包
python setup.py install

# 跑单个爬虫
python example/baiduSpider.py

# 跑多个爬虫
python example/run.py
```
