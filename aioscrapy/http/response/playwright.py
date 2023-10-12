from typing import Optional, Any

from aioscrapy.http.response.text import TextResponse


class PlaywrightResponse(TextResponse):
    def __init__(
            self,
            *args,
            text: str = '',
            cache_response: Optional[dict] = None,
            driver: Optional["PlaywrightDriver"] = None,
            driver_pool: Optional["WebDriverPool"] = None,
            intercept_request: Optional[dict] = None,
            **kwargs
    ):
        self.driver = driver
        self.driver_pool = driver_pool
        self._text = text
        self.cache_response = cache_response or {}
        self.intercept_request = intercept_request
        super().__init__(*args, **kwargs)

    async def release(self):
        self.driver_pool and self.driver and await self.driver_pool.release(self.driver)

    @property
    def text(self):
        return self._text or super().text

    @text.setter
    def text(self, text):
        self._text = text

    def get_response(self, key) -> Any:
        return self.cache_response.get(key)
