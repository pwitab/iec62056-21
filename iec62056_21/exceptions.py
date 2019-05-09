class Iec6205621Exception(Exception):
    """General IEC62056-21 Exception"""


class Iec6205621ParseError(Iec6205621Exception):
    """Error in parsing IEC62056-21 data"""


class ValidationError(Iec6205621Exception):
    """Not valid data error"""


class TooManyValuesReturned(Iec6205621Exception):
    """If a request for a single value returned more than one value"""


class NoDataReturned(Iec6205621Exception):
    """No data was returned"""


class Iec6206521BaseErrorParser:
    """
    Error messages are contained in DataSets and values without unit. Their format is
    manufacturer specific so the library can only define a way to handle them not the
    exact implementation.
    The DummyErrorParser will we used as standard that ignores all errors.
    An ErrorParser should take an answer response and parse each data set in it to see
    if there is any errors. It should raise appropriate exceptions.
    """

    def __init__(self):
        pass

    def check_for_errors(self, answer_response):
        raise NotImplementedError("check_for_errors must be implemented in subclass")


class DummyErrorParser(Iec6206521BaseErrorParser):
    """
    A Dummy parser that fits in as default. Should be overridden if you want to define
    an error parser.
    """

    def check_for_errors(self, answer_response):
        pass
