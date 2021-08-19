import re
from typing import *
import attr

from iec62056_21.exceptions import Iec6205621ParseError, ValidationError
from iec62056_21 import constants, utils

ENCODING = "latin-1"


# Regex to be used for parsing data. Compiled once for reuse later.
regex_data_set = re.compile(r"^(.+)\((.*)\)")
regex_data_set_data = re.compile(r"^(.*)\*(.*)")
regex_data_just_value = re.compile(r"^\((.*)\)")


class Iec6205621Data:
    """
    Base class for IEC 62056-21 messages.
    """

    def to_representation(self):
        raise NotImplementedError("Needs to be implemented in subclass")

    def to_bytes(self):
        """
        Ensures the correct encoding to bytes.
        """
        return self.to_representation().encode(constants.ENCODING)

    @classmethod
    def from_representation(cls, string_data):
        raise NotImplementedError("Needs to be implemented in subclass")

    @classmethod
    def from_bytes(cls, bytes_data):
        """
        Ensures the correct decoding from  bytes.
        """

        return cls.from_representation(bytes_data.decode(constants.ENCODING))


@attr.s(auto_attribs=True)
class DataSet(Iec6205621Data):

    """
    The data set is the smallest component of a response.
    It consists of an address and value with optional unit. in the format of
    {address}({value}*{unit})
    """

    EXCLUDE_CHARS = ["(", ")", "/", "!"]

    value: str
    address: Optional[str] = attr.ib(default=None)
    unit: Optional[str] = attr.ib(default=None)

    def to_representation(self) -> str:
        if self.unit is not None and self.address is not None:
            return f"{self.address}({self.value}*{self.unit})"
        elif self.address is not None and self.unit is None:
            return f"{self.address}({self.value})"
        else:
            if self.value is None:
                return f"()"
            else:
                return f"({self.value})"

    @classmethod
    def from_representation(cls, data_set_string: str):
        just_value = regex_data_just_value.search(data_set_string)

        if just_value:
            return cls(address=None, value=just_value.group(1), unit=None)

        first_match = regex_data_set.search(data_set_string)
        if not first_match:
            raise Iec6205621ParseError(
                f"Unable to find address and data in {data_set_string}"
            )
        address = first_match.group(1)
        values_data = first_match.group(2)
        second_match = regex_data_set_data.search(values_data)
        if second_match:
            return cls(
                address=address, value=second_match.group(1), unit=second_match.group(2)
            )

        else:
            return cls(address=address, value=values_data, unit=None)


@attr.s(auto_attribs=True)
class DataLine(Iec6205621Data):
    """
    A data line is a list of data sets.
    """

    data_sets: List[DataSet]

    def to_representation(self):
        sets_representation = [_set.to_representation() for _set in self.data_sets]
        return "".join(sets_representation)

    @classmethod
    def from_representation(cls, string_data: str):
        """
        Is a list of data sets  id(value*unit)id(value*unit)
        need to split after each ")"
        """
        separator = ")"
        data_sets = list()
        _string_data = string_data
        for x in range(0, string_data.count(separator)):
            index = _string_data.find(separator) + 1
            data_set_string = _string_data[:index]
            _string_data = _string_data[index:]
            data_set = DataSet.from_representation(data_set_string=data_set_string)
            data_sets.append(data_set)

        return cls(data_sets=data_sets)


@attr.s(auto_attribs=True)
class DataBlock(Iec6205621Data):
    """
    A data block is a list of DataLines, each ended with a the line end characters
    \n\r
    """

    data_lines: List[DataLine]

    def to_representation(self) -> str:
        lines_rep = [
            (line.to_representation() + constants.LINE_END) for line in self.data_lines
        ]
        return "".join(lines_rep)

    @classmethod
    def from_representation(cls, string_data: str):
        lines = string_data.splitlines()
        data_lines = [DataLine.from_representation(line) for line in lines]
        return cls(data_lines)


@attr.s(auto_attribs=True)
class ReadoutDataMessage(Iec6205621Data):
    data_block: DataBlock

    def to_representation(self) -> str:
        data = (
            f"{constants.STX}{self.data_block.to_representation()}{constants.END_CHAR}"
            f"{constants.LINE_END}{constants.ETX}"
        )

        return utils.add_bcc(data)

    @classmethod
    def from_representation(cls, string_data: str):
        _in_data = string_data

        if not utils.bcc_valid(string_data):
            raise ValueError("BCC not valid")

        _in_data = _in_data[1:-5]  # remove stx and !<cr><lf>ETX bcc

        data_block = DataBlock.from_representation(_in_data)

        return cls(data_block=data_block)


@attr.s(auto_attribs=True)
class CommandMessage(Iec6205621Data):
    ALLOWED_COMMANDS: ClassVar[List[str]] = ["P", "W", "R", "E", "B"]
    ALLOWES_COMMAND_TYPES: ClassVar[List[str]] = [
        "0",
        "1",
        "2",
        "3",
        "4",
        "5",
        "6",
        "7",
        "8",
        "9",
    ]

    command: str = attr.ib(validator=attr.validators.in_(ALLOWED_COMMANDS))
    command_type: str = attr.ib(validator=attr.validators.in_(ALLOWES_COMMAND_TYPES))
    data_set: Optional[DataSet] = attr.ib(default=None)

    def to_representation(self) -> str:
        header = f"{constants.SOH}{self.command}{self.command_type}"
        if self.data_set:
            body = f"{constants.STX}{self.data_set.to_representation()}{constants.ETX}"
        else:
            body = f"{constants.ETX}"

        message = f"{header}{body}"

        return utils.add_bcc(message)

    @classmethod
    def from_representation(cls, string_data):
        if not utils.bcc_valid(string_data):
            raise ValueError("BCC not valid")
        _message = string_data[:-1]  # remove bcc
        header = _message[:3]
        body = _message[3:]

        command = header[1]
        command_type = header[2]
        data_set = DataSet.from_representation(body[1:-1])

        return cls(command, command_type, data_set)

    @classmethod
    def for_single_read(cls, address, additional_data=None):
        if additional_data:
            _add_data = additional_data
        else:
            _add_data = ""
        data_set = DataSet(value=_add_data, address=address)
        return cls(command="R", command_type="1", data_set=data_set)

    @classmethod
    def for_single_write(cls, address, value):
        data_set = DataSet(value=value, address=address)
        return cls(command="W", command_type="1", data_set=data_set)


@attr.s(auto_attribs=True)
class AnswerDataMessage(Iec6205621Data):

    data_block: DataBlock
    cached_data: Optional[List[DataSet]] = attr.ib(default=None, init=False)

    @property
    def data(self):
        if not self.cached_data:
            self.get_all_data_sets()

        return self.cached_data

    def get_all_data_sets(self):
        data_sets = list()

        for line in self.data_block.data_lines:
            for data_set in line.data_sets:
                data_sets.append(data_set)

        self.cached_data = data_sets

    def to_representation(self):
        # TODO: this is not valid in case reading out partial blocks.
        rep = f"{constants.STX}{self.data_block.to_representation()}{constants.ETX}"

        return utils.add_bcc(rep)

    @classmethod
    def from_representation(cls, string_data):
        _in_data = string_data

        if not utils.bcc_valid(string_data):
            raise ValueError("BCC not valid")

        _in_data = _in_data[1:-2]  # remove stx -- etx bcc

        data_block = DataBlock.from_representation(_in_data)

        return cls(data_block=data_block)


@attr.s(auto_attribs=True)
class RequestMessage(Iec6205621Data):
    device_address: str = attr.ib(default="")

    def to_representation(self) -> str:
        return (
            f"{constants.START_CHAR}{constants.REQUEST_CHAR}{self.device_address}"
            f"{constants.END_CHAR}{constants.LINE_END}"
        )

    @classmethod
    def from_representation(cls, string_data):
        device_address = string_data[2:-3]
        return cls(device_address)


@attr.s(auto_attribs=True)
class AckOptionSelectMessage(Iec6205621Data):
    """"""

    baud_char: str
    mode_char: str
    protocol_char: str = attr.ib(default="0")

    def to_representation(self):
        return f"{constants.ACK}{self.protocol_char}{self.baud_char}{self.mode_char}{constants.LINE_END}"

    @classmethod
    def from_representation(cls, string_data):
        protocol_char = string_data[1]
        baud_char = string_data[2]
        mode_char = string_data[3]
        return cls(baud_char, mode_char, protocol_char=protocol_char)


@attr.s(auto_attribs=True)
class IdentificationMessage(Iec6205621Data):

    identification: str
    manufacturer: str
    switchover_baudrate_char: str

    def to_representation(self):
        return (
            f"{constants.START_CHAR}{self.manufacturer}{self.switchover_baudrate_char}\\"
            f"{self.identification}{constants.LINE_END}"
        )

    @classmethod
    def from_representation(cls, string_data):
        manufacturer = string_data[1:4]
        switchover_baudrate_char = string_data[4]
        identification = string_data[6:-2]

        return cls(identification, manufacturer, switchover_baudrate_char)
