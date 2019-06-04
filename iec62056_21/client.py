import time
import logging

from iec62056_21 import messages, constants, transports, exceptions

logger = logging.getLogger(__name__)


class Iec6205621Client:
    """
    A client class for IEC 62056-21. Only validated with meters using mode C.
    """

    BAUDRATES_MODE_C = {
        "0": 300,
        "1": 600,
        "2": 1200,
        "3": 2400,
        "4": 4800,
        "5": 9600,
        "6": 19200,
    }
    ALLOWED_MODES = [
        "readout",
        "programming",
        "binary",
        "manufacturer6",
        "manufacturer7",
        "manufacturer8",
        "manufacturer9",
    ]
    MODE_CONTROL_CHARACTER = {
        "readout": "0",
        "programming": "1",
        "binary": "2",
        "manufacturer6": "6",
        "manufacturer7": "7",
        "manufacturer8": "8",
        "manufacturer9": "9",
    }
    SHORT_REACTION_TIME = 0.02
    REACTION_TIME = 0.2

    def __init__(
        self,
        transport,
        device_address="",
        password="00000000",
        battery_powered=False,
        error_parser_class=exceptions.DummyErrorParser,
    ):

        self.transport = transport
        self.device_address = device_address
        self.password = password
        self.battery_powered = battery_powered
        self.identification = None
        self.switchover_baudrate_char = None
        self.manufacturer_id = None
        self.use_short_reaction_time = False
        self.error_parser = error_parser_class()

    @property
    def switchover_baudrate(self):
        """
        Shoirtcut to get the baud rate for the switchover.
        """
        return self.BAUDRATES_MODE_C.get(self.switchover_baudrate_char)

    def read_single_value(self, address, additional_data="1"):
        """
        Reads a value from an address in the device.

        :param address:
        :param additional_data:
        :return:
        """
        # TODO Can't find documentation on why the additional_data of 1 is needed.

        request = messages.CommandMessage.for_single_read(address, additional_data)
        logger.info(f"Sending read request: {request}")
        self.transport.send(request.to_bytes())

        response = self.read_response()

        if len(response.data) > 1:
            raise exceptions.TooManyValuesReturned(
                f"Read of one value returned {len(response.data)}"
            )
        if len(response.data) == 0:
            raise exceptions.NoDataReturned(f"Read returned no data")

        logger.info(f"Received response: {response}")
        # Just return the data, not in a list since it is just one.
        return response.data[0]

    def write_single_value(self, address, data):
        """
        Writes a value to an address in the device.

        :param address:
        :param data:
        :return:
        """

        request = messages.CommandMessage.for_single_write(address, data)
        logger.info(f"Sending write request: {request}")
        self.transport.send(request.to_bytes())

        ack = self._recv_ack()
        if ack == constants.ACK:
            logger.info(f"Write request accepted")
            return
        elif ack == constants.NACK:
            # TODO: implement retry and raise proper error.
            raise ValueError(f"Received NACK upon sending {request}")
        else:
            raise ValueError(
                f"Received invalid response {ack} to write request {request}"
            )

    def connect(self):
        """
        Connect to the device
        """
        self.transport.connect()

    def disconnect(self):
        """
        Close connection to device
        """
        self.transport.disconnect()

    def startup(self):
        """
        Initial communication to start the session with the device. Sends a
        RequestMessage and receives identification message.
        """

        if self.battery_powered:
            self.send_battery_power_startup_sequence()
        logger.info("Staring init sequence")
        self.send_init_request()

        ident_msg = self.read_identification()

        # Setting the baudrate to the one propsed by the device.
        self.switchover_baudrate_char = str(ident_msg.switchover_baudrate_char)

        self.identification = ident_msg.identification
        self.manufacturer_id = ident_msg.manufacturer

        # If a meter transmits the third letter (last) in lower case, the minimum
        # reaction time for the device is 20 ms instead of 200 ms.
        if self.manufacturer_id[-1].islower():
            self.use_short_reaction_time = True

    def access_programming_mode(self):
        """
        Goes through the steps to set the meter in programming mode.
        Returns the password challenge request to be acted on.
        """

        self.startup()

        self.ack_with_option_select("programming")

        self.transport.switch_baudrate(self.switchover_baudrate)

        # receive password request
        pw_req = self.read_response()

        return pw_req

    def standard_readout(self):
        """
        Goes through the steps to read the standard readout response from the device.
        """
        self.startup()
        self.ack_with_option_select("readout")
        self.transport.switch_baudrate(self.switchover_baudrate)
        logger.info(f"Reading standard readout from device.")
        response = self.read_response()
        return response

    def send_password(self, password=None):
        """
        On receiving the password challenge request one must handle the password
        challenge according to device specification and then send the password.
        :param password:
        """
        _pw = password or self.password
        data_set = messages.DataSet(value=_pw)
        cmd = messages.CommandMessage(command="P", command_type="1", data_set=data_set)
        logger.info("Sending password to meter")
        self.transport.send(cmd.to_bytes())

    def send_break(self):
        """
        Sending the break message to indicate that one wants to stop the
        communication.
        """
        logger.info("Sending BREAK message to end communication")
        break_msg = messages.CommandMessage(command="B", command_type=0, data_set=None)
        self.transport.send(break_msg.to_bytes())

    def ack_with_option_select(self, mode):
        """
        After receiving the identification one needs to respond with an ACK including
        the different options for the session. The main usage is to control the
        mode. readout, programming, or manufacturer specific. The baudrate change used
        will be the one proposed by the device in the identification message.

        :param mode:
        """
        mode_char = self.MODE_CONTROL_CHARACTER[mode]
        ack_message = messages.AckOptionSelectMessage(
            mode_char=mode_char, baud_char=self.switchover_baudrate_char
        )
        logger.info(f"Sending AckOptionsSelect message: {ack_message}")
        self.transport.send(ack_message.to_bytes())
        self.rest()

    def send_init_request(self):
        """
        The init request tells the device they you want to start a session with it.
        When using the optical interface on the device there is no need to send the
        device address in the init request since there can be only one meter.
        Over TCP or bus-like transports like RS-485 you will need to specify the meter
         you want to talk to by adding the address in the request.

        """
        if self.transport.TRANSPORT_REQUIRES_ADDRESS:
            request = messages.RequestMessage(device_address=self.device_address)
        else:
            request = messages.RequestMessage()

        logger.info(f"Sending request message: {request}")
        self.transport.send(request.to_bytes())
        self.rest()

    def read_identification(self):
        """
        Properly receive the identification message and parse it.
        """

        data = self.transport.simple_read(start_char="/", end_char="\x0a")

        identification = messages.IdentificationMessage.from_bytes(data)
        logger.info(f"Received identification message: {identification}")
        return identification

    def send_battery_power_startup_sequence(self, fast=False):
        """
        Battery powered devices require a startup sequence of null bytes to
        activate
        There is a normal and a fast start up sequence defined in the protocol.

        Normal:
            Null chars should be sent to the device for 2.1-2.3 seconds with a maximum
            of 0,5 seconds between them.
            After the last charachter the client shall wait 1.5-1,7 seconds until it
            sends the request message

        :param fast:
        """
        if fast:
            raise NotImplemented("Fast startup sequence is not yet implemented")

        timeout = 2.2
        duration = 0
        start_time = time.time()
        logger.info("Sending battery startup sequence")
        while duration < timeout:
            out = b"\x00"
            self.transport.send(out)
            self.rest(0.2)
            duration = time.time() - start_time
        logger.info("Startup Sequence finished")

        self.rest(1.5)

    def _recv_ack(self):
        """
        Simple way of receiving an ack or nack.
        """
        ack = self.transport.recv(1).decode(constants.ENCODING)
        return ack

    def read_response(self, timeout=None):
        """
        Reads the response from a device and parses it to the correct message type.

        :param timeout:
        """
        data = self.transport.read()
        if data.startswith(b"\x01"):
            # We probably received a password challenge
            return messages.CommandMessage.from_bytes(data)
        else:
            response = messages.AnswerDataMessage.from_bytes(data)
            self.error_parser.check_for_errors(response)
            return response

    @property
    def reaction_time(self):
        """
        The device can define two different reaction times. Depending if the third
        letter in the manufacturer ID in the identification request is in lower case the
        shorter reaction time is used.
        """
        if self.use_short_reaction_time:
            return self.SHORT_REACTION_TIME
        else:
            return self.REACTION_TIME

    def rest(self, duration=None):
        """
        The protocol needs some timeouts between reads and writes to enable the device
        to properly parse a message and return the result.
        """

        _duration = duration or (self.reaction_time * 1.25)
        logger.debug(f"Resting for {_duration} seconds")
        time.sleep(_duration)

    @classmethod
    def with_serial_transport(
        cls,
        port,
        device_address="",
        password="00000000",
        battery_powered=False,
        error_parser_class=exceptions.DummyErrorParser,
    ):
        """
        Initiates the client with a serial transport.

        :param port:
        :param device_address:
        :param password:
        :param battery_powered:
        :return:
        """
        transport = transports.SerialTransport(port=port)
        return cls(
            transport, device_address, password, battery_powered, error_parser_class
        )

    @classmethod
    def with_tcp_transport(
        cls,
        address,
        device_address="",
        password="00000000",
        battery_powered=False,
        error_parser_class=exceptions.DummyErrorParser,
    ):
        """
        Initiates the client with a TCP Transport.

        :param address:
        :param device_address:
        :param password:
        :param battery_powered:
        :return:
        """
        transport = transports.TcpTransport(address=address)
        return cls(
            transport, device_address, password, battery_powered, error_parser_class
        )
