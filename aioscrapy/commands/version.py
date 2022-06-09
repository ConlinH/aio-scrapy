import aioscrapy
from aioscrapy.commands import AioScrapyCommand


class Command(AioScrapyCommand):
    default_settings = {
        'LOG_ENABLED': False,
        'SPIDER_LOADER_WARN_ONLY': True
    }

    def syntax(self):
        return "[-v]"

    def short_desc(self):
        return "Print aioscrapy version"

    def add_options(self, parser):
        AioScrapyCommand.add_options(self, parser)

    def run(self, args, opts):
        print(f"aioscrapy {aioscrapy.__version__}")
