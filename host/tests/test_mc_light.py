from types import SimpleNamespace
from unittest import mock

import mc_light


def _port(vid, device, description="", interface=""):
    return SimpleNamespace(vid=vid, device=device, description=description, interface=interface)


def test_find_light_port_returns_matching_device():
    ports = [_port(0x1234, "COM1"), _port(0x2E8A, "COM3")]
    with mock.patch.object(mc_light.list_ports, "comports", return_value=ports):
        assert mc_light.find_light_port() == "COM3"


def test_find_light_port_prefers_cdc2_data_port():
    # 同一块板子的两路 CDC,description 带 CDC2 的 data 口应优先于回退的"序号更大"
    ports = [_port(0x2E8A, "COM1", description="Board CDC"),
             _port(0x2E8A, "COM2", description="Board CDC - CDC2")]
    with mock.patch.object(mc_light.list_ports, "comports", return_value=ports):
        assert mc_light.find_light_port() == "COM2"


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


def test_main_unknown_arg_returns_0_and_skips_serial():
    with mock.patch.object(mc_light, "find_light_port") as find:
        assert mc_light.main(["bogus"]) == 0
        find.assert_not_called()


def test_main_no_arg_returns_0():
    assert mc_light.main([]) == 0


def test_main_no_device_returns_0_and_skips_send():
    with mock.patch.object(mc_light, "find_light_port", return_value=None), \
         mock.patch.object(mc_light, "send_command") as send:
        assert mc_light.main(["on"]) == 0
        send.assert_not_called()


def test_main_sends_correct_byte_when_device_found():
    with mock.patch.object(mc_light, "find_light_port", return_value="COM3"), \
         mock.patch.object(mc_light, "send_command") as send:
        assert mc_light.main(["off"]) == 0
        send.assert_called_once_with("COM3", b"0")


def test_main_returns_0_when_send_raises():
    with mock.patch.object(mc_light, "find_light_port", return_value="COM3"), \
         mock.patch.object(mc_light, "send_command", side_effect=OSError("busy")):
        assert mc_light.main(["on"]) == 0


def test_commands_map_wait():
    assert mc_light.COMMANDS["wait"] == b"2"


def test_main_sends_two_for_wait_when_device_found():
    with mock.patch.object(mc_light, "find_light_port", return_value="COM3"), \
         mock.patch.object(mc_light, "send_command") as send:
        assert mc_light.main(["wait"]) == 0
        send.assert_called_once_with("COM3", b"2")
