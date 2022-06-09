from abc import ABCMeta, abstractmethod


class AbsDupeFilterBase(metaclass=ABCMeta):

    @classmethod
    @abstractmethod
    def from_spider(cls, spider):
        """Returns instance from crawler.

        Parameters
        ----------
        spider : aioscrapy.crawler.spider

        Returns
        -------
        RFPDupeFilter
            Instance of RFPDupeFilter.

        """

    @abstractmethod
    def request_seen(self, request):
        """Returns True if request was already seen.

        Parameters
        ----------
        request : aioscrapy.http.Request

        Returns
        -------
        bool
        """

    @abstractmethod
    def close(self, reason):
        """Delete data on close. Called by aioscrapy's scheduler.

        Parameters
        ----------
        reason : str, optional

        """

    @abstractmethod
    def log(self, request, spider):
        """Logs given request.

        Parameters
        ----------
        request : aioscrapy.http.Request
        spider : aioscrapy.spiders.Spider

        """
