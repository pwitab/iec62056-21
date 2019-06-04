import pytest

from iec62056_21.utils import calculate_bcc, add_bcc


class TestBcc:
    def test_bcc_bytes1(self):
        data = bytes.fromhex("01573202433030332839313033323430393232333929031b")
        correct_bcc = chr(data[-1]).encode("latin-1")
        bcc = calculate_bcc(data[1:-1])
        assert bcc == correct_bcc

    def test_bcc_bytes_2(self):
        data = b"\x01P0\x02(1234567)\x03P"
        correct_bcc = chr(data[-1]).encode("latin-1")
        bcc = calculate_bcc(data[1:-1])
        assert bcc == correct_bcc

    def test_bcc_string(self):
        data = "\x01P0\x02(1234567)\x03P"
        correct_bcc = data[-1]
        bcc = calculate_bcc(data[1:-1])
        assert bcc == correct_bcc

    def test_add_bcc1(self):
        data = "\x01P0\x02(1234567)\x03"
        correct_data = "\x01P0\x02(1234567)\x03P"
        with_bcc = add_bcc(data)
        assert with_bcc == correct_data
