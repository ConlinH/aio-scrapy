from types import SimpleNamespace

import pytest

from aioscrapy import Request
from aioscrapy.core.downloader.handlers import resolve_redirect_enabled


class DummySettings(dict):
    def getbool(self, name, default=False):
        return bool(self.get(name, default))


@pytest.mark.parametrize(
    ('global_enabled', 'dont_redirect', 'expected'),
    [
        (True, None, True),
        (False, None, False),
        (True, True, False),
        (False, True, False),
        (True, False, True),
        (False, False, True),
    ],
)
def test_resolve_redirect_enabled(global_enabled, dont_redirect, expected):
    meta = {} if dont_redirect is None else {'dont_redirect': dont_redirect}
    request = Request('https://example.com', meta=meta)
    settings = DummySettings(REDIRECT_ENABLED=global_enabled)

    assert resolve_redirect_enabled(request, settings) is expected


def test_redirect_option_accepts_settings_like_objects():
    settings = SimpleNamespace(getbool=lambda name, default: default)
    request = Request('https://example.com')

    assert resolve_redirect_enabled(request, settings) is True
