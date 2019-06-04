import pytest

from iec62056_21 import messages, exceptions, constants


class TestDataSets:

    data_set_with_unit = "3.1.0(100*kWh)"
    data_set_without_unit = "3.1.0(100)"
    not_valid_data = '"Tralalalala'

    def test_from_string_with_unit(self):
        ds = messages.DataSet.from_representation(self.data_set_with_unit)
        assert ds.value == "100"
        assert ds.address == "3.1.0"
        assert ds.unit == "kWh"

    def test_from_bytes_with_unit(self):
        ds_bytes = self.data_set_with_unit.encode("latin-1")
        ds = messages.DataSet.from_representation(self.data_set_with_unit)
        assert ds.value == "100"
        assert ds.address == "3.1.0"
        assert ds.unit == "kWh"

    def test_to_string_with_unit(self):
        ds = messages.DataSet(value="100", address="3.1.0", unit="kWh")
        assert ds.to_representation() == self.data_set_with_unit

    def test_to_byte_with_unit(self):
        ds = messages.DataSet(value="100", address="3.1.0", unit="kWh")
        assert ds.to_bytes() == self.data_set_with_unit.encode(constants.ENCODING)

    def test_from_string_without_unit(self):
        ds = messages.DataSet.from_representation(self.data_set_without_unit)
        assert ds.value == "100"
        assert ds.address == "3.1.0"
        assert ds.unit == None

    def test_from_bytes_without_unit(self):
        ds_bytes = self.data_set_without_unit.encode("latin-1")
        ds = messages.DataSet.from_representation(self.data_set_without_unit)
        assert ds.value == "100"
        assert ds.address == "3.1.0"
        assert ds.unit == None

    def test_to_string_without_unit(self):
        ds = messages.DataSet(value="100", address="3.1.0", unit=None)
        assert ds.to_representation() == self.data_set_without_unit

    def test_to_byte_without_unit(self):
        ds = messages.DataSet(value="100", address="3.1.0", unit=None)
        assert ds.to_bytes() == self.data_set_without_unit.encode(constants.ENCODING)

    def test_invalid_data(self):
        with pytest.raises(exceptions.Iec6205621ParseError):
            ds = messages.DataSet.from_representation(self.not_valid_data)


class TestBase:
    def test_to_bytes(self):
        with pytest.raises(NotImplementedError):
            messages.Iec6205621Data().to_bytes()

    def test_from_bytes(self):
        with pytest.raises(NotImplementedError):
            messages.Iec6205621Data().from_bytes(b"1235")


class TestDataLine:
    def test_from_representation(self):
        string_data = "12(12*kWh)13(13*kWh)14(14*kwh)"

        dl = messages.DataLine.from_representation(string_data)

        assert len(dl.data_sets) == 3
        assert dl.data_sets[0].value == "12"
        assert dl.data_sets[0].address == "12"
        assert dl.data_sets[0].unit == "kWh"

    def test_to_representation(self):
        dl = messages.DataLine(
            data_sets=[
                messages.DataSet(address="3:14", value="314", unit="kWh"),
                messages.DataSet(address="4:15", value="415", unit="kWh"),
            ]
        )

        rep = dl.to_representation()

        assert rep == "3:14(314*kWh)4:15(415*kWh)"


class TestDataBlock:
    def test_from_representation_single_line(self):
        string_data = "12(12*kWh)13(13*kWh)14(14*kwh)\r\n"

        db = messages.DataBlock.from_representation(string_data)

        assert len(db.data_lines) == 1

    def test_from_representation_several_lines(self):
        string_data = (
            "12(12*kWh)13(13*kWh)14(14*kwh)\r\n"
            "12(12*kWh)13(13*kWh)14(14*kwh)\r\n"
            "12(12*kWh)13(13*kWh)14(14*kwh)\r\n"
        )
        db = messages.DataBlock.from_representation(string_data)

        assert len(db.data_lines) == 3

    def test_to_representation_several_lines(self):

        db = messages.DataBlock(
            data_lines=[
                messages.DataLine(
                    data_sets=[
                        messages.DataSet(address="3:14", value="314", unit="kWh"),
                        messages.DataSet(address="4:15", value="415", unit="kWh"),
                    ]
                ),
                messages.DataLine(
                    data_sets=[
                        messages.DataSet(address="3:14", value="314", unit="kWh"),
                        messages.DataSet(address="4:15", value="415", unit="kWh"),
                    ]
                ),
                messages.DataLine(
                    data_sets=[
                        messages.DataSet(address="3:14", value="314", unit="kWh"),
                        messages.DataSet(address="4:15", value="415", unit="kWh"),
                    ]
                ),
            ]
        )

        assert db.to_representation() == (
            "3:14(314*kWh)4:15(415*kWh)\r\n"
            "3:14(314*kWh)4:15(415*kWh)\r\n"
            "3:14(314*kWh)4:15(415*kWh)\r\n"
        )

        def test_to_representation_single_line(self):
            db = messages.DataBlock(
                data_lines=[
                    messages.DataLine(
                        data_sets=[
                            messages.DataSet(address="3:14", value="314", unit="kWh"),
                            messages.DataSet(address="4:15", value="415", unit="kWh"),
                        ]
                    )
                ]
            )

            assert db.to_representation() == "3:14(314*kWh)4:15(415*kWh)\r\n"


class TestAnswerDataMessage:
    def test_from_representation(self):
        data = "\x023:171.0(0)\x03\x12"

        am = messages.AnswerDataMessage.from_representation(data)

        assert am.data_block.data_lines[0].data_sets[0].value == "0"
        assert am.data_block.data_lines[0].data_sets[0].address == "3:171.0"
        assert am.data[0].value == "0"
        assert am.data[0].address == "3:171.0"

    def test_from_representation_invalid_bcc_raises_value_error(self):
        data = "\x023:171.0(0)\x03\x11"
        with pytest.raises(ValueError):
            am = messages.AnswerDataMessage.from_representation(data)

    def test_to_representation(self):
        db = messages.DataBlock(
            data_lines=[
                messages.DataLine(
                    data_sets=[
                        messages.DataSet(address="3:14", value="314", unit="kWh"),
                        messages.DataSet(address="4:15", value="415", unit="kWh"),
                    ]
                )
            ]
        )

        am = messages.AnswerDataMessage(data_block=db)

        assert am.to_representation() == "\x023:14(314*kWh)4:15(415*kWh)\r\n\x03\x04"


class TestReadoutDataMessage:
    def test_to_representation(self):
        rdm = messages.ReadoutDataMessage(
            data_block=messages.DataBlock(
                data_lines=[
                    messages.DataLine(
                        data_sets=[
                            messages.DataSet(address="3:14", value="314", unit="kWh"),
                            messages.DataSet(address="4:15", value="415", unit="kWh"),
                        ]
                    )
                ]
            )
        )

        assert rdm.to_representation() == '\x023:14(314*kWh)4:15(415*kWh)\r\n!\r\n\x03"'

    def test_from_representation(self):

        rdm = messages.ReadoutDataMessage.from_representation(
            '\x023:14(314*kWh)4:15(415*kWh)\r\n!\r\n\x03"'
        )
        print(rdm)
        assert len(rdm.data_block.data_lines) == 1
        assert len(rdm.data_block.data_lines[0].data_sets) == 2

    def test_invalid_bcc_raises_error(self):
        with pytest.raises(ValueError):
            rdm = messages.ReadoutDataMessage.from_representation(
                "\x023:14(314*kWh)4:15(415*kWh)\r\n!\r\n\x03x"
            )


class TestCommandMessage:
    def test_command_message_to_representation(self):
        cm = messages.CommandMessage(
            command="R",
            command_type=1,
            data_set=messages.DataSet(address="1.8.0", value=1),
        )

        assert cm.to_representation() == "\x01R1\x021.8.0(1)\x03k"

    def test_from_representation(self):
        data = "\x01P0\x02(1234567)\x03P"
        cm = messages.CommandMessage.from_representation(data)

        assert cm.command == "P"
        assert cm.command_type == 0
        assert cm.data_set.value == "1234567"
        assert cm.data_set.address is None
        assert cm.data_set.unit is None

    def test_invalid_command_raises_value_error(self):
        with pytest.raises(ValueError):
            cm = messages.CommandMessage(
                command="X",
                command_type=1,
                data_set=messages.DataSet(address="1.8.0", value=1),
            )

    def test_invalid_command_type_raises_value_error(self):
        with pytest.raises(ValueError):
            cm = messages.CommandMessage(
                command="R",
                command_type=12,
                data_set=messages.DataSet(address="1.8.0", value=1),
            )

    def test_to_representation_without_data_set(self):
        # like the break command

        break_msg = messages.CommandMessage(command="B", command_type=0, data_set=None)

        assert break_msg.to_representation() == "\x01B0\x03q"

    def test_from_representation_invalid_bcc_raise_value_error(self):
        data = "\x01P0\x02(1234567)\x03X"
        with pytest.raises(ValueError):
            cm = messages.CommandMessage.from_representation(data)

    def test_for_single_read(self):
        cm = messages.CommandMessage.for_single_read(address="1.8.0")

        assert cm.command == "R"
        assert cm.command_type == 1
        assert cm.data_set.address == "1.8.0"

        cm = messages.CommandMessage.for_single_read(
            address="1.8.0", additional_data="1"
        )

        assert cm.command == "R"
        assert cm.command_type == 1
        assert cm.data_set.address == "1.8.0"
        assert cm.data_set.value == "1"

    def test_for_single_write(self):
        cm = messages.CommandMessage.for_single_write(address="1.8.0", value="123")

        assert cm.command == "W"
        assert cm.command_type == 1
        assert cm.data_set.address == "1.8.0"
        assert cm.data_set.value == "123"


class TestRequestMessage:
    def test_to_representation(self):
        rm = messages.RequestMessage(device_address="45678903")

        assert rm.to_representation() == "/?45678903!\r\n"

    def test_to_representation_without_address(self):
        rm = messages.RequestMessage()

        assert rm.to_representation() == "/?!\r\n"

    def test_from_representation(self):

        in_data = "/?45678903!\r\n"

        rm = messages.RequestMessage.from_representation(in_data)

        assert rm.device_address == "45678903"


class TestAckOptionSelectMessage:
    def test_to_representation(self):
        aosm = messages.AckOptionSelectMessage(mode_char="1", baud_char="5")

        assert aosm.to_representation() == "\x06051\r\n"

    def test_from_representation(self):
        aosm = messages.AckOptionSelectMessage.from_representation("\x06051\r\n")

        assert aosm.mode_char == "1"
        assert aosm.baud_char == "5"


class TestIdentificationMessage:
    def test_to_representation(self):

        im = messages.IdentificationMessage(
            identification="2EK280", manufacturer="Els", switchover_baudrate_char="6"
        )

        assert im.to_representation() == "/Els6\\2EK280\r\n"

    def test_from_representation(self):
        im = messages.IdentificationMessage.from_representation("/Els6\\2EK280\r\n")

        assert im.identification == "2EK280"
        assert im.manufacturer == "Els"
        assert im.switchover_baudrate_char == "6"
