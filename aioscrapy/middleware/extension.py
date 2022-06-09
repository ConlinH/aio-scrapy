"""
The Extension Manager

See documentation in docs/topics/extensions.rst
"""
from aioscrapy.middleware.absmanager import AbsMiddlewareManager
from aioscrapy.utils.conf import build_component_list


class ExtensionManager(AbsMiddlewareManager):

    component_name = 'extension'

    @classmethod
    def _get_mwlist_from_settings(cls, settings):
        return build_component_list(settings.getwithbase('EXTENSIONS'))
