from aioscrapy import Request, Spider, logger


class BaiduSpider(Spider):
    name = 'baidu'

    start_urls = ['https://hanyu.baidu.com/zici/s?wd=黄&query=黄']

    async def parse(self, response):
        logger.info(response)
        item = {
            'pingyin': response.xpath('//div[@id="pinyin"]/span/b/text()').get(),
            'fan': response.xpath('//*[@id="traditional"]/span/text()').get(),
        }
        yield item

        new_character = response.xpath('//a[@class="img-link"]/@href').getall()
        for character in new_character:
            new_url = 'https://hanyu.baidu.com/zici' + character
            yield Request(new_url, callback=self.parse, dont_filter=True)


if __name__ == '__main__':
    BaiduSpider.start()
