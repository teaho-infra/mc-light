from types import SimpleNamespace
from unittest import mock

import mc_light


def _port(vid, device):
    return SimpleNamespace(vid=vid, device=device)


def test_find_light_port_returns_matching_device():
    ports = [_port(0x1234, "COM1"), _port(0x2E8A, "COM3")]
    with mock.patch.object(mc_light.list_ports, "comports", return_value=ports):
        assert mc_light.find_light_port() == "COM3"


def test_find_light_port_returns_none_when_no_match():
    ports = [_port(0x1234, "COM1"), _port(None, "COM2")]
    with mock.patch.object(mc_light.list_ports, "comports", return_value=ports):
        assert mc_light.find_light_port() is None


def test_send_command_opens_with_timeouts_and_writes():
    fake_ser = mock.MagicMock()
    fake_ser.__enter__.return_value = fake_ser
    with mock.patch.object(mc_light.serial, "Serial", return_value=fake_ser) as ctor:
        mc_light.send_command("COM3", b"1", timeout=1.0)
    ctor.assert_called_once_with("COM3", timeout=1.0, write_timeout=1.0)
    fake_ser.write.assert_called_once_with(b"1")


def test_commands_map_on_off():
    assert mc_light.COMMANDS["on"] == b"1"
    assert mc_light.COMMANDS["off"] == b"0"
