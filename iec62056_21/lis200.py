from datetime import datetime, timedelta, timezone
import re
import attr

from iec62056_21.messages import Iec6205621Data
from iec62056_21 import constants, utils, exceptions


def datetime_is_aware(d):
    return d.tzinfo is not None and d.tzinfo.utcoffset(d) is not None


def format_datetime(dt):
    if datetime_is_aware(dt):
        raise ValueError("Lis200 does not handle timezone aware datetime objects.")
    return dt.strftime("%Y-%m-%d,%H:%M:%S")


def parse_datetime(datetime_string, utc_offset=None):
    date = datetime.strptime(datetime_string, "%Y-%m-%d,%H:%M:%S")

    if utc_offset:
        offset_tz = timezone(timedelta(seconds=utc_offset))
        date = date.replace(tzinfo=offset_tz)
    return date


class ArchiveReadoutCommand(Iec6205621Data):
    """
    A spacial readout commnad is needed to read archives.

    Each data row contains the measurements save at a certain point in time.
    Any range of the data in the archive can be read out. How to read the archive is
    specified withing the data in the readout command. within the parenthesises.

    For attributes !=0 there is only one data row in the answer.

    :param int archive: Number of the archive to be read.
    :param str attribute: Attribute to read. Defaults to `'0'`.
        * 0 = Value
        * 1 = Rights of Access
        * 2 = Description
        * 3 = Units (Text)
        * 4 = Source
        * 5 = Units (Code)
        * 6 = Format
        * 7 = Data type
        * 8 = Settable source of archive (Device dependant)
        * 9 = Reserved
        * A = Number of data sets in range.
    :param int position: The column number of the controlling value in the archive.
        Example if timestamp is the third value in the archive you need to set the
        position to 3 to specify a time range. Defaults to `1`. Max value is 99.
    :param str start: Lower limit (oldest data row) of the archive field to be read out.
        Allowed lenght is 17 so it can contain timestamps. Defaults to `''` and if not
        present the oldest available row is used as lower limit
    :param str end: Upper limit (newest data row) of the archive field to be read out.
        Allowed lenght is 17 so it can contain timestamps. Defaults to `''` and if not
        present the newest available data row is used as the upper limit.
    :param bool partial_blocks: Indicates if readout should be done via partial blocks.
        Defaults to `False`.
    :param int rows_per_block: If partial_blocks is True then rows per block controls
        how many rows is sent in each partial block. Defaults to `100`.
    """

    def __init__(
        self,
        archive,
        start="",
        end="",
        position=1,
        attribute="0",
        partial_blocks=False,
        rows_per_block=10,
    ):
        self.archive = archive
        self.attribute = attribute
        self.position = position
        self.start = start
        self.end = end
        self.partial_blocks = partial_blocks
        self.rows_per_block = rows_per_block

    @classmethod
    def from_representation(cls, string_data):
        # TODO: regex?
        pass

    def to_representation(self):
        if self.partial_blocks:
            command = "R3"
            rows_per_block = self.rows_per_block
        else:
            command = "R1"
            rows_per_block = ""

        rep = (
            f"{constants.SOH}{command}{constants.STX}{self.archive}:V.{self.attribute}"
            f"({self.position};{self.start};{self.end};{rows_per_block}){constants.ETX}"
        )
        return utils.add_bcc(rep)

    def __repr__(self):
        return (
            f"{self.__class__.__name__}("
            f"archive={self.archive!r},"
            f"start={self.start!r},"
            f"end={self.end!r},"
            f"position={self.position!r},"
            f"attribute={self.attribute!r},"
            f"partial_blocks={self.partial_blocks!r},"
            f"rows_per_block={self.rows_per_block!r})"
        )


@attr.s
class ArchiveDataPoint:

    timestamp = attr.ib()
    value = attr.ib()
    address = attr.ib()
    unit = attr.ib()


class ArchiveReadout:
    """
    A normal archive readout is just returning the values to conserve data.
    To be able to know the address and unit of the value we need to read other
    attributes of the archive.
    addresses = attribute 4
    units = attribute 3
    By combining all the results it is possible to get an AnswerMessage with
    addresses, values and units for all data sets.
    :return:
    """

    def __init__(self, values, addresses, units, datetime_position, utc_offset):

        self.values = values
        self.addresses = addresses
        self.units = units
        self.datetime_position = datetime_position
        self.utc_offset = utc_offset

    @property
    def data(self):
        data_points = list()
        _addresses = self.addresses.data_block.data_lines[0].data_sets
        _units = self.units.data_block.data_lines[0].data_sets

        for line in self.values.data_block.data_lines:

            # other positions are refered without initial 0. But that wont work when
            # referenceing a list.
            datetime_index = self.datetime_position - 1

            timestamp = parse_datetime(
                datetime_string=line.data_sets[datetime_index].value,
                utc_offset=self.utc_offset,
            )

            for i, data_set in enumerate(line.data_sets):

                # Strip of all left leading zeros since we don't need them.
                _address = _addresses[i].value.lstrip("0")
                if _units[i].value:
                    _unit = _units[i].value
                else:
                    _unit = None
                _value = data_set.value
                _timestamp = timestamp

                data_point = ArchiveDataPoint(
                    timestamp=_timestamp, value=_value, address=_address, unit=_unit
                )

                data_points.append(data_point)

        return data_points


class Lis200Exception(Exception):
    """General LIS200 Exception"""


class Lis200ProtocolError(Lis200Exception):
    """General error in Lis200 protocol"""


class WrongAddress(Lis200ProtocolError):
    """Code: 1, Wrong (unknown) address"""


class ObjectNotAvailableError(Lis200ProtocolError):
    """Code: 2, Wrong address, object not available"""


class EntityForObjectNotAvailable(Lis200ProtocolError):
    """Code: 3, Wrong address, entity for object not available"""


class UnknownAttributeError(Lis200ProtocolError):
    """Code: 4, Wrong address, unknown attribute"""


class AttributeForObjectNotAvailableError(Lis200ProtocolError):
    """Code: 5, Wrong address, attribute for object not available"""


class ValueOutsideOfAllowedRangeError(Lis200ProtocolError):
    """Code: 6, Value outside of allowed range"""


class WriteOnConstantNotExecutableError(Lis200ProtocolError):
    """Code: 9, Write command on constant not executable"""


class NoInputAllowedError(Lis200ProtocolError):
    """Code: 11, No value range available since no input is allowed"""


class WrongInputError(Lis200ProtocolError):
    """Code: 13, Wrong input"""


class UnknownUnitsError(Lis200ProtocolError):
    """Code: 14, Unknown units code """


class WrongAccessCodeError(Lis200ProtocolError):
    """Code: 17, Wrong access code"""


class NoReadAuthorizationError(Lis200ProtocolError):
    """Code: 18, No read authorization"""


class NoWriteAuthorization(Lis200ProtocolError):
    """Code 19, No write authorization"""


class FunctionLockedError(Lis200ProtocolError):
    """Code: 20, Function is locked"""


class ArchiveNumberNotAvailableError(Lis200ProtocolError):
    """Code: 100, Archive number not available"""


class ValuePositionNotAvailableError(Lis200ProtocolError):
    """Code, 101, Value position not available"""


class ArchiveEmptyError(Lis200ProtocolError):
    """Code: 103, Archive empty"""


class LowerLimitNotFound(Lis200ProtocolError):
    """Code: 104, Lower limit (From-value) not found"""


class UpperLimitNotFound(Lis200ProtocolError):
    """Code: 105, Upper limit (To-value) not found"""


class MaxLimitOpenArchivesError(Lis200ProtocolError):
    """Code: 108, Maximum limit of simultaneous opened archives exceeded"""


class ArchiveEntryOverwrittenWhileReadingError(Lis200ProtocolError):
    """Code: 109, Archive entry was overwritten while reading out"""


class CrcErrorInRecordError(Lis200ProtocolError):
    """Code: 110, CRC error in archive data record"""


class SourceNotAllowedError(Lis200ProtocolError):
    """Code: 180, Source not allowed"""


class TelegramSyntaxError(Lis200ProtocolError):
    """Code: 200, Syntax error in telegram"""


class TelegramWrongPasswordError(Lis200ProtocolError):
    """Code: 201, Wrong password in telegram"""


class EepromReadError(Lis200ProtocolError):
    """Code: 222, EEPROM read error"""


class EepromWriteError(Lis200ProtocolError):
    """Code: 223, EEPROM write error"""


class EncodeChangeError(Lis200ProtocolError):
    """Code: 249, Encoder mode not possible / Counter reading cannot be changed"""


class Lis200ErrorParser(exceptions.Iec6206521BaseErrorParser):
    """
    Error messages in LIS200 are predefined. They all begin with a # and contain an
    error number.

    Code    Meaning
    ----    -------
    1       Wrong (unknown) address
    2       Wrong address, object not available
    3       Wrong address, entity for object not available
    4       Wrong address, unknown attribute
    5       Wrong address, attribute for object not available
    6       Value outside of allowed range
    9       Write command on constant not executable
    11      No value range available since no input is allowed
    13      Wrong input
    14      Unknown units code
    17      Wrong access code
    18      No read authorization
    19      No write authorization
    20      Function is locked
    100     Archive number not available
    101     Value position not available
    103     Archive empty
    104     Lower limit (From-value) not found
    105     Upper limit (To-value) not found
    108     Maximum limit of simultaneous opened archives exceeded
    109     Archive entry was overwritten while reading out
    110     CRC error in archive data record
    180     Source not allowed
    200     Syntax error in telegram
    201     Wrong password in telegram
    222     EEPROM read error
    223     EEPROM write error
    249     Encoder mode not possible / Counter reading cannot be changed
    """

    ERROR_MAP = {
        1: WrongAddress,
        2: ObjectNotAvailableError,
        3: EntityForObjectNotAvailable,
        4: UnknownAttributeError,
        5: AttributeForObjectNotAvailableError,
        6: ValueOutsideOfAllowedRangeError,
        9: WriteOnConstantNotExecutableError,
        11: NoInputAllowedError,
        13: WrongInputError,
        14: UnknownUnitsError,
        17: WrongAccessCodeError,
        18: NoReadAuthorizationError,
        19: NoWriteAuthorization,
        20: FunctionLockedError,
        100: ArchiveNumberNotAvailableError,
        101: ValuePositionNotAvailableError,
        103: ArchiveEmptyError,
        104: LowerLimitNotFound,
        105: UpperLimitNotFound,
        108: MaxLimitOpenArchivesError,
        109: ArchiveEntryOverwrittenWhileReadingError,
        110: CrcErrorInRecordError,
        180: SourceNotAllowedError,
        200: TelegramSyntaxError,
        201: TelegramWrongPasswordError,
        222: EepromReadError,
        223: EepromWriteError,
        249: EncodeChangeError,
    }

    def __init__(self):
        super().__init__()
        self.regex_for_error = re.compile(r"^#(\d{4})")

    def check_for_errors(self, answer_response):
        errors = list()
        for item in answer_response.data:
            error = re.search(self.regex_for_error, item.value)
            if error:
                error_text = error.group(1)
                error_nr = int(error_text.lstrip("0"))
                errors.append(error_nr)

        # just raise the first error
        if errors:
            raise self.ERROR_MAP[errors[0]]()
