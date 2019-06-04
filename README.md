
# IEC 62056-21

[![CircleCI](https://circleci.com/gh/pwitab/iec62056-21/tree/master.svg?style=svg)](https://circleci.com/gh/pwitab/iec62056-21/tree/master)
[![Coverage Status](https://coveralls.io/repos/github/pwitab/iec62056-21/badge.svg)](https://coveralls.io/github/pwitab/iec62056-21)

A Python library for IEC 62056-21, Direct Local Data Exchange of Energy Meters. 
Former IEC 61107 or IEC 1107

## Installation

We only support python 3.6+

Install via pip:

```
pip install iec62056-21
```

## About IEC 62056-21

IEC 62056-21 (earlier IEC 61107 or sometimes just IEC 1107, is an international 
standard for a computer protocol to read utility meters. It is designed to operate 
over any media, including the Internet. A meter sends ASCII (in modes A..D) or 
HDLC (mode E) data to a nearby hand-held unit (HHU) using a serial port. The physical 
media are usually either modulated light, sent with an LED and received with a 
photodiode, or a pair of wires, usually modulated by a 20mA current loop. The protocol 
is usually half-duplex.


## Limitations of this library.

* At the moment we only support Mode C.
* We assume that only protocol mode Normal is used.

## Example usage:

Reading a meter using a optical usb probe via the D0-interface.

```python
from iec62056_21.client import Iec6205621Client

client = Iec6205621Client.with_serial_transport(port='/dev/tty_something')

password_challange = client.access_programming_mode()

client.send_password('00000000')  # Common standard password

data_answer = client.read_value('1.8.0')
```

```python
from iec62056_21.client import Iec6205621Client

client = Iec6205621Client.with_tcp_transport(address=('192.168.0.1', 8000), device_address='12345678', password='00000000')

password_challange = client.access_programming_mode()

client.send_password('00000000')  # Common standard password

data_answer = client.read_value('1.8.0')
```


## Derivative protocols

Some manufacturer are using a derivative protocol to IEC 62056-21. They comply with 
most things but might for example not use the access request features according to 
standard or they have a slightly different flow in command execution

This library can be used with some of them. You just need to be aware of the differences.
We provide special handlers for some unique parts that is included in this library. 
They might be split into separate libraries in the future.

### LIS-200

A protocol for Elster devices. Main difference is that they have the concept of 
locks instead of password and instead of answering the password request you need to 
write the password to a certain register.

## Development

This library is developed by Palmlund Wahlgren Innovative Technology AB in Sweden and 
is used in our multi utility AMR solution: [Utilitarian](https://docs.utilitarian.io)

## Contributing

*   Check for open issues or open a fresh issue to start a discussion around a feature 
    idea or a bug.
*   Fork the repository on GitHub to start making your changes to the master branch (or 
    branch off of it).
*   Write a test which shows that the bug was fixed or that the feature works as expected.
*   Send a pull request and bug the maintainer until it gets merged and published.
