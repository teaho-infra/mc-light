"""mc-light host hook script: send on/off over USB serial to the XIAO RP2040."""
import sys

import serial
from serial.tools import list_ports

XIAO_VID = 0x2E8A


def find_light_port(vid=XIAO_VID):
    """Return the device name of the first serial port matching `vid`, else None."""
    for port in list_ports.comports():
        if port.vid == vid:
            return port.device
    return None


COMMANDS = {"on": b"1", "off": b"0"}


def send_command(port, byte, timeout=1.0):
    """Open `port`, write `byte`, close. Raises on failure."""
    with serial.Serial(port, timeout=timeout, write_timeout=timeout) as ser:
        ser.write(byte)
