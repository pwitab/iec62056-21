import pytest
from iec62056_21 import exceptions, client, transports


class TestIec6205621Client:
    def test_with_no_address_when_required_raises_client_error(self):
        with pytest.raises(exceptions.Iec6205621ClientError):
            c = client.Iec6205621Client.with_tcp_transport(("192.168.1.1", 5000))

    def test_can_create_client_with_tcp_transport(self):
        c = client.Iec6205621Client.with_tcp_transport(
            "192.168.1.1", device_address="00000000"
        )

    def test_no_address_when_required_raises_client_error(self):
        trans = transports.TcpTransport(address=("192.168.1.1", 5000))
        with pytest.raises(exceptions.Iec6205621ClientError):
            c = client.Iec6205621Client(transport=trans)

    def test_can_create_client_tcp_transport(self):
        trans = transports.TcpTransport(address=("192.168.1.1", 5000))
        c = client.Iec6205621Client(transport=trans, device_address="00000000")
