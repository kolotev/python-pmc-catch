from pmc.singleton import singleton
from typing import Tuple


class ExceptionCounter:
    def __init__(self):
        self._warnings_count = 0
        self._errors_count = 0

    @property
    def warnings_count(self) -> int:
        """
        :return: warnings count
        """
        return self._warnings_count

    @warnings_count.setter
    def warnings_count(self, value):
        self._warnings_count = value

    @property
    def errors_count(self) -> int:
        """
        :return: errors count
        """
        return self._errors_count

    @errors_count.setter
    def errors_count(self, value):
        self._errors_count = value

    def counts(self) -> Tuple[int, int]:
        """
        :return: errors_count, warnings_count
        """
        return self.errors_count, self.warnings_count


@singleton
class ExceptionCounterGlobal(ExceptionCounter):
    def reset(self):
        self.__init__()
