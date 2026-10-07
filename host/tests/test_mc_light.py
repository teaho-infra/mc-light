import os
from types import SimpleNamespace
from unittest import mock

import mc_light


def _port(vid, device, description="", interface="", hwid="", location=""):
    return SimpleNamespace(vid=vid, device=device, description=description,
                           interface=interface, hwid=hwid, location=location)


# --- _select_data_port 纯函数:跨平台核心判定 ---


def test_select_prefers_cdc2_description():
    ports = [_port(0x2E8A, "COM1", description="Board CDC"),
             _port(0x2E8A, "COM2", description="Board CDC - CDC2")]
    assert mc_light._select_data_port(ports) == "COM2"


def test_select_prefers_data_in_interface():
    ports = [_port(0x2E8A, "COM1", interface="CDC CDC"),
             _port(0x2E8A, "COM2", interface="CDC data")]
    assert mc_light._select_data_port(ports) == "COM2"


def test_select_returns_none_when_empty():
    assert mc_light._select_data_port([]) is None


def test_select_uses_interface_number_when_no_description_hint():
    # Windows:description 无 CDC2/data,靠 MI 接口号区分(data=MI_02)
    ports = [_port(0x2886, "COM4", hwid="USB\\VID_2886&PID_0042&REV_0100&MI_00"),
             _port(0x2886, "COM3", hwid="USB\\VID_2886&PID_0042&REV_0100&MI_02")]
    assert mc_light._select_data_port(ports) == "COM3"


def test_select_com_number_ordering_does_not_matter():
    # COM9 < COM10 字符串排序陷阱:接口号必须优先于 COM 号
    ports = [_port(0x2886, "COM9", hwid="...&MI_00"),
             _port(0x2886, "COM10", hwid="...&MI_02")]
    assert mc_light._select_data_port(ports) == "COM10"


def test_select_uses_location_tail_when_no_mi():
    # 无 MI_ 标记时,location 尾段(&0&0002)是接口号
    ports = [_port(0x2886, "COM3", location="6&2C349E3&0&0000"),
             _port(0x2886, "COM4", location="6&2C349E3&0&0002")]
    assert mc_light._select_data_port(ports) == "COM4"


def test_select_returns_none_when_no_interface_info():
    # 描述无 CDC2/data、无接口号时不得猜测,返回 None
    ports = [_port(0x2886, "COM3"), _port(0x2886, "COM4")]
    assert mc_light._select_data_port(ports) is None


def test_select_multi_board_picks_data_ports():
    ports = [
        _port(0x2886, "COM5", hwid="...&MI_02"),   # 板A data
        _port(0x2886, "COM6", hwid="...&MI_00"),   # 板A console
        _port(0x2886, "COM8", hwid="...&MI_02"),   # 板B data
        _port(0x2886, "COM7", hwid="...&MI_00"),   # 板B console
    ]
    assert mc_light._select_data_port(ports) in ("COM5", "COM8")


def test_select_description_wins_over_interface_number():
    # 描述明确 CDC2 时,即使接口号不是最大也优先
    ports = [_port(0x2E8A, "COM1", description="Board CDC - CDC2",
                   hwid="...&MI_00"),
             _port(0x2E8A, "COM2", description="Board CDC",
                   hwid="...&MI_02")]
    assert mc_light._select_data_port(ports) == "COM1"


# --- find_light_port 显式端口与兜底 ---


def test_explicit_port_env_overrides_selection():
    with mock.patch.dict(os.environ, {"MC_LIGHT_PORT": "COM10"}), \
         mock.patch.object(mc_light, "_select_data_port") as sel:
        assert mc_light.find_light_port() == "COM10"
        sel.assert_not_called()


def test_explicit_port_env_used_without_device():
    with mock.patch.dict(os.environ, {"MC_LIGHT_PORT": "COM10"}), \
         mock.patch.object(mc_light, "_select_data_port") as sel:
        assert mc_light.find_light_port() == "COM10"
        sel.assert_not_called()


def test_find_generic_passes_vid_filtered_ports():
    # generic 路径:mock list_ports.comports,验证 VID 过滤后交给 _select_data_port
    if mc_light.IS_WINDOWS:
        return  # 仅非 Windows 分支有 list_ports 模块
    ports = [_port(0x1234, "COM1"), _port(0x2E8A, "COM3", hwid="...&MI_02")]
    with mock.patch.dict(os.environ, {}, clear=True), \
         mock.patch.object(mc_light, "_select_data_port", return_value="COM3") as sel, \
         mock.patch("mc_light.list_ports") as lp:
        lp.comports.return_value = ports
        assert mc_light.find_light_port() == "COM3"
        sel.assert_called_once()
        assert sel.call_args[0][0][0].device == "COM3"


# --- send_command / main ---


def test_commands_map_on_off():
    assert mc_light.COMMANDS["on"] == b"1"
    assert mc_light.COMMANDS["off"] == b"0"
    assert mc_light.COMMANDS["wait"] == b"2"


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


def test_main_sends_two_for_wait_when_device_found():
    with mock.patch.object(mc_light, "find_light_port", return_value="COM3"), \
         mock.patch.object(mc_light, "send_command") as send:
        assert mc_light.main(["wait"]) == 0
        send.assert_called_once_with("COM3", b"2")


def test_send_command_generic_uses_pyserial():
    # 非 Windows 分支:pyserial Serial 上下文写字节
    if mc_light.IS_WINDOWS:
        return  # Windows 分支用 ctypes,不测 pyserial 路径
    fake_ser = mock.MagicMock()
    fake_ser.__enter__.return_value = fake_ser
    with mock.patch.object(mc_light.serial, "Serial", return_value=fake_ser) as ctor:
        mc_light.send_command("COM3", b"1", timeout=1.0)
    ctor.assert_called_once_with("COM3", timeout=1.0, write_timeout=1.0)
    fake_ser.write.assert_called_once_with(b"1")
