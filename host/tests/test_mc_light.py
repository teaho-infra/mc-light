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
