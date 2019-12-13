import typing


class MetricsBase:
    """ Common base class for calculating and reporting metrics"""
    def __init__(self):
        self.report = "Not Defined"

    def __str__(self) -> str:
        return self.report

    def build_report(self) -> str:
        raise NotImplementedError

    def write_report(self, filename: str) -> typing.NoReturn:
        raise NotImplementedError

