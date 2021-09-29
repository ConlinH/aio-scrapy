

# aioscrapy
将基于twisted的scrapy/scrapy-redis改成基于asyncio, 保留了几乎所有的scrapy/scrapy-reids功能

### 声明
仅供学习使用，禁止项目源码用于任何目的，由此引发的任何法律纠纷与本人无关

### 安装

``` 
# python版本==3.7

# 下载安装
pip install git+https://github.com/conlin-huang/aioscrapy.git
```
#### 使用
##### 跑单个爬虫
```python example/demo2/baiduSpider.py```

##### 跑多个爬虫
```python example/demo2/run.py```

##### 运行爬虫项目
```python example/demo1/start.py```

##### 部署分布式爬虫
```python
# 步骤一: 安装scrapyd
# pip install scrapyd

# 步骤二: 修改scrapyd配置
# 使用aioscrapy/scrapyd/default_scrapyd.conf替换scrapyd的默认配置

# 步骤三: 启动scrapyd

# 步骤四: 上传爬虫
# 双击执行example/demo1下的deploy.bat
# 或者直接执行 python deploy.py server1

# 启动爬虫
# curl http://localhost:6800/schedule.json -d project=demo1 -d spider=baidu
```
