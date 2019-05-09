import re
import typing

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


class DataSet(Iec6205621Data):

    """
    The data set is the smallest component of a response.
    It consists of an address and value with optional unit. in the format of
    {address}({value}*{unit})
    """

    EXCLUDE_CHARS = ["(", ")", "/", "!"]

    def __init__(self, address, value, unit=None, no_address=False):

        # TODO: in programming mode, protocol mode C the value can be up to 128 chars

        self.address = address
        self.value = value
        self.unit = unit

    def to_representation(self):
        if self.unit:
            return f"{self.address}({self.value}*{self.unit})"
        else:
            return f"{self.address}({self.value})"

    @classmethod
    def from_representation(cls, data_set_string):
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

    def __repr__(self):
        return (
            f"{self.__class__.__name__}("
            f"address={self.address!r}, "
            f"value={self.value!r}, "
            f"unit={self.unit!r}"
            f")"
        )


class DataLine(Iec6205621Data):
    """
    A data line is a list of data sets.
    """

    def __init__(self, data_sets):
        self.data_sets: typing.List[DataSet] = data_sets

    def to_representation(self):
        sets_representation = [_set.to_representation() for _set in self.data_sets]
        return "".join(sets_representation)

    @classmethod
    def from_representation(cls, string_data):
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

    def __repr__(self):
        return f"{self.__class__.__name__}(" f"data_sets={self.data_sets!r}" f")"


class DataBlock(Iec6205621Data):
    """
    A data block is a list of DataLines, each ended with a the line end characters
    \n\r
    """

    def __init__(self, data_lines):
        self.data_lines = data_lines

    def to_representation(self):
        lines_rep = [
            (line.to_representation() + constants.LINE_END) for line in self.data_lines
        ]
        return "".join(lines_rep)

    @classmethod
    def from_representation(cls, string_data: str):
        lines = string_data.splitlines()
        data_lines = [DataLine.from_representation(line) for line in lines]
        return cls(data_lines)

    def __repr__(self):
        return f"{self.__class__.__name__}(data_lines={self.data_lines!r})"


class ReadoutDataMessage(Iec6205621Data):
    def __init__(self, data_block):
        self.data_block = data_block

    def to_representation(self):
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

    def __repr__(self):
        return f"{self.__class__.__name__}(data_block={self.data_block!r})"


class CommandMessage(Iec6205621Data):
    allowed_commands = ["P", "W", "R", "E", "B"]
    allowed_command_types = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]

    def __init__(self, command, command_type, data_set):
        self.command = command
        self.command_type = command_type
        self.data_set = data_set

        if command not in self.allowed_commands:
            raise ValueError(f"{command} is not an allowed command")
        if command_type not in self.allowed_command_types:
            raise ValueError(f"{command_type} is not an allowed command type")

    def to_representation(self):
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
        command_type = int(header[2])
        data_set = DataSet.from_representation(body[1:-1])

        return cls(command, command_type, data_set)

    @classmethod
    def for_single_read(cls, address, additional_data=None):
        if additional_data:
            _add_data = additional_data
        else:
            _add_data = ""
        data_set = DataSet(value=_add_data, address=address)
        return cls(command="R", command_type=1, data_set=data_set)

    @classmethod
    def for_single_write(cls, address, value):
        data_set = DataSet(value=value, address=address)
        return cls(command="W", command_type=1, data_set=data_set)

    def __repr__(self):
        return (
            f"{self.__class__.__name__}("
            f"command={self.command!r}, "
            f"command_type={self.command_type!r}, "
            f"data_set={self.data_set!r}"
            f")"
        )


class AnswerDataMessage(Iec6205621Data):
    def __init__(self, data_block):
        self.data_block = data_block
        self._data = None

    @property
    def data(self):
        if not self._data:
            self._get_all_data_sets()

        return self._data

    def _get_all_data_sets(self):
        data_sets = list()

        for line in self.data_block.data_lines:
            for set in line.data_sets:
                data_sets.append(set)

        self._data = data_sets

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

    def __repr__(self):
        return f"{self.__class__.__name__}(data_block={self.data_block!r})"


class RequestMessage(Iec6205621Data):
    def __init__(self, device_address=""):
        self.device_address = device_address

    def to_representation(self):
        return (
            f"{constants.START_CHAR}{constants.REQUEST_CHAR}{self.device_address}"
            f"{constants.END_CHAR}{constants.LINE_END}"
        )

    @classmethod
    def from_representation(cls, string_data):
        device_address = string_data[2:-3]
        return cls(device_address)

    def __repr__(self):
        return f"{self.__class__.__name__}(device_address={self.device_address!r})"


class AckOptionSelectMessage(Iec6205621Data):
    """
    Only support protocol mode 0: Normal
    """

    def __init__(self, baud_char, mode_char):
        self.baud_char = baud_char
        self.mode_char = mode_char

    def to_representation(self):
        return f"{constants.ACK}0{self.baud_char}{self.mode_char}{constants.LINE_END}"

    @classmethod
    def from_representation(cls, string_data):
        baud_char = string_data[2]
        mode_char = string_data[3]
        return cls(baud_char, mode_char)

    def __repr__(self):
        return (
            f"{self.__class__.__name__}("
            f"baud_char={self.baud_char!r}, "
            f"mode_char={self.mode_char!r}"
            f")"
        )


class IdentificationMessage(Iec6205621Data):
    def __init__(self, identification, manufacturer, switchover_baudrate_char):
        self.identification = identification
        self.manufacturer = manufacturer
        self.switchover_baudrate_char = switchover_baudrate_char

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

    def __repr__(self):
        return (
            f"{self.__class__.__name__}("
            f"identification={self.identification!r}, "
            f"manufacturer={self.manufacturer!r}, "
            f"switchover_baudrate_char={self.switchover_baudrate_char!r}"
            f")"
        )
