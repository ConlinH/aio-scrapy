"""
Module containing all HTTP related classes

Use this module (instead of the more specific ones) when importing Headers,
Request and Response outside this module.
"""

from aioscrapy.http.request import Request
from aioscrapy.http.request.form import FormRequest
from aioscrapy.http.request.json_request import JsonRequest

from aioscrapy.http.response import Response
from aioscrapy.http.response.html import HtmlResponse
from aioscrapy.http.response.xml import XmlResponse
from aioscrapy.http.response.text import TextResponse
