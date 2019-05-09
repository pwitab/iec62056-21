from iec62056_21 import constants


def bcc_valid(message):
    bcc = message[-1]
    to_calc = message[:-1]
    calc = add_bcc(to_calc)
    if message == calc:
        return True
    else:
        return False


def add_bcc(message):
    """
    Returns the message with BCC added.
    Data to use starts after STX and ends with but includes ETX
    If there is a SOH in the message the calculation should be done from there.
    """

    if isinstance(message, str):
        _message = message.encode(constants.ENCODING)
        return _add_bcc(_message).decode(constants.ENCODING)
    return _add_bcc(message)


def _add_bcc(message: bytes):
    start_bcc_index = 1
    soh_index = message.find(constants.SOH.encode(constants.ENCODING))
    if soh_index == -1:
        # SOH not found
        stx_index = message.find(constants.STX.encode(constants.ENCODING))
        if stx_index == -1:
            raise IndexError("No SOH or STX found i message")
        start_bcc_index = stx_index + 1
    else:
        start_bcc_index = soh_index + 1

    data_for_bcc = message[start_bcc_index:]
    bcc = calculate_bcc(data_for_bcc)
    return message + bcc


def calculate_bcc(data):
    """
    Calculate BCC.
    """
    if isinstance(data, str):
        _bcc = _calculate_bcc(data.encode(constants.ENCODING))
        return _bcc.decode(constants.ENCODING)

    return _calculate_bcc(data)


def _calculate_bcc(bytes_data: bytes):
    bcc = 0
    for b in bytes_data:
        x = b & 0x7F
        bcc ^= x
        bcc &= 0x7F
    return bcc.to_bytes(length=1, byteorder="big")


def ensure_bytes(data):
    if isinstance(data, str):
        return data.encode(constants.ENCODING)
    elif isinstance(data, bytes):
        return data
    else:
        raise ValueError(f"data:{data!r} cant be converted to bytes")
