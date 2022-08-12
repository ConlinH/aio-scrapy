"""
This module implements the FormRequest class which is a more convenient class
(than Request) to generate Requests based on form data.

See documentation in docs/topics/request-response.rst
"""
from typing import List, Optional, Tuple, Union
from urllib.parse import urlencode

from aioscrapy.http.request import Request
from aioscrapy.utils.python import to_bytes, is_listlike

FormdataType = Optional[Union[dict, List[Tuple[str, str]]]]


class FormRequest(Request):
    valid_form_methods = ['GET', 'POST']

    def __init__(self, *args, formdata: FormdataType = None, **kwargs) -> None:
        if formdata and kwargs.get('method') is None:
            kwargs['method'] = 'POST'

        super().__init__(*args, **kwargs)

        if formdata:
            items = formdata.items() if isinstance(formdata, dict) else formdata
            form_query: str = _urlencode(items, self.encoding)
            if self.method == 'POST':
                self.headers.setdefault('Content-Type', 'application/x-www-form-urlencoded')
                self._set_body(form_query)
            else:
                self._set_url(self.url + ('&' if '?' in self.url else '?') + form_query)


def _urlencode(seq, enc):
    values = [(to_bytes(k, enc), to_bytes(v, enc))
              for k, vs in seq
              for v in (vs if is_listlike(vs) else [vs])]
    return urlencode(values, doseq=1)
