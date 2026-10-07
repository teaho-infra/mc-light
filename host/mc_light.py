"""mc-light host hook script: send on/off over USB serial to the XIAO RP2040.

跨平台:
- Windows:纯标准库(winreg 枚举 COM 口 + ctypes 写串口),零 pip 依赖。
- 其它平台(含 WSL/Ubuntu):回退到 pyserial。
"""
import os
import re
import sys

IS_WINDOWS = sys.platform == "win32"

if not IS_WINDOWS:
    import serial
    from serial.tools import list_ports

# 兼容两种 XIAO RP2040:Raspberry Pi 官方 VID 与 Seeed 自家 VID
XIAO_VIDS = (0x2E8A, 0x2886)

# 环境变量:显式指定 COM 口(Windows)/ttyACM(Ubuntu),绕过自动识别
ENV_PORT = "MC_LIGHT_PORT"


def _parse_mi(text):
    """从 hwid/location 文本提取 USB 接口号(MI_xx 或 LOCATION 尾段)。

    CircuitPython 的 boot.py 打开 console + data 两路 CDC:
    console 占用接口 0, data 占用接口 2(Windows 表现为 MI_00 / MI_02)。
    接口号越大越可能是 data 口。返回 None 表示拿不到。
    """
    m = re.search(r"MI_(\d+)", text, re.IGNORECASE)
    if m:
        return int(m.group(1))
    m = re.search(r"&0&(\d+)$", text)
    if m:
        return int(m.group(1))
    return None


def _select_data_port(matches):
    """从 VID 已过滤的候选端口里挑 data 口。`matches` 元素需具备
    .device/.description/.interface/.hwid/.location 属性(模拟 pySerial 对象)。

    优先级:
      1. description/interface 含 "CDC2"/"data" 的口(直连判断)。
      2. 按 USB 接口号(MI_xx)取最大——data 口接口号大于 console。
      3. 都无法区分时返回 None,绝不猜。
    绝不按 device 字符串排序:Windows COM 号不保证顺序(COM9 < COM10)。
    """
    if not matches:
        return None
    for p in matches:
        desc = (p.description or "") + " " + (p.interface or "")
        if "CDC2" in desc or "data" in desc.lower():
            return p.device
    with_mi = [(p, _parse_mi(" ".join(str(x or "") for x in (p.hwid, p.location))))
               for p in matches]
    known = [(p, mi) for p, mi in with_mi if mi is not None]
    if known:
        return max(known, key=lambda kv: kv[1])[0].device
    return None


def _find_light_port_generic():
    """非 Windows 路径:用 pyserial 枚举,再交 _select_data_port 判定。"""
    explicit = os.environ.get(ENV_PORT)
    if explicit:
        return explicit

    matches = [p for p in list_ports.comports() if p.vid in XIAO_VIDS]
    return _select_data_port(matches)


if IS_WINDOWS:
    # ------------------------------------------------------------------
    # Windows 零依赖路径
    # ------------------------------------------------------------------
    import ctypes
    import ctypes.wintypes as wt
    import winreg

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateFileW.restype = wt.HANDLE
    kernel32.CreateFileW.argtypes = [wt.LPCWSTR, wt.DWORD, wt.DWORD, wt.LPVOID,
                                     wt.DWORD, wt.DWORD, wt.HANDLE]
    kernel32.WriteFile.argtypes = [wt.HANDLE, wt.LPVOID, wt.DWORD,
                                   ctypes.POINTER(wt.DWORD), wt.LPVOID]
    kernel32.SetCommTimeouts.argtypes = [wt.HANDLE, wt.LPVOID]
    kernel32.EscapeCommFunction.argtypes = [wt.HANDLE, wt.DWORD]
    kernel32.CloseHandle.argtypes = [wt.HANDLE]

    GENERIC_READ = 0x80000000
    GENERIC_WRITE = 0x40000000
    OPEN_EXISTING = 3
    FILE_ATTRIBUTE_NORMAL = 0x80
    SETDTR = 5
    CLRDTR = 6
    INVALID_HANDLE = ctypes.c_void_p(-1).value

    class _COMMTIMEOUTS(ctypes.Structure):
        _fields_ = [("ReadIntervalTimeout", wt.DWORD),
                    ("ReadTotalTimeoutConstant", wt.DWORD),
                    ("ReadTotalTimeoutMultiplier", wt.DWORD),
                    ("WriteTotalTimeoutConstant", wt.DWORD),
                    ("WriteTotalTimeoutMultiplier", wt.DWORD)]

    _VID_RE = re.compile(r"VID_([0-9A-Fa-f]{4})")
    _MI_RE = re.compile(r"MI_(\d+)", re.IGNORECASE)

    def _enumerate_usb_ports():
        """枚举注册表 Enum\\USB 下所有 VID/PID 设备实例,返回 pySerial 风格对象列表,
        每项带 .device/.vid/.description/.interface/.hwid/.location。
        """
        from types import SimpleNamespace
        base = r"SYSTEM\CurrentControlSet\Enum\USB"
        results = []
        try:
            root = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, base)
        except OSError:
            return results
        try:
            for i in range(winreg.QueryInfoKey(root)[0]):
                sub = winreg.EnumKey(root, i)
                sub_path = base + "\\" + sub
                # 递归一层:USB\<VID&PID>\<实例>\Device Parameters\PortName
                try:
                    inst = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, sub_path)
                except OSError:
                    continue
                try:
                    for j in range(winreg.QueryInfoKey(inst)[0]):
                        inst_name = winreg.EnumKey(inst, j)
                        inst_path = sub_path + "\\" + inst_name
                        port = None
                        try:
                            pp = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                                inst_path + r"\Device Parameters")
                            try:
                                port, _ = winreg.QueryValueEx(pp, "PortName")
                            finally:
                                winreg.CloseKey(pp)
                        except OSError:
                            pass
                        if port is None:
                            continue
                        try:
                            k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, inst_path)
                            try:
                                hwids, _ = winreg.QueryValueEx(k, "HardwareID")
                                try:
                                    desc, _ = winreg.QueryValueEx(k, "FriendlyName")
                                except OSError:
                                    desc = ""
                            finally:
                                winreg.CloseKey(k)
                        except OSError:
                            hwids = []
                            desc = ""
                        hwid0 = hwids[0] if hwids else ""
                        m = _VID_RE.search(hwid0 or sub)
                        vid = int(m.group(1), 16) if m else None
                        mi = _MI_RE.search(hwid0)
                        mi_n = int(mi.group(1)) if mi else _parse_mi(hwid0)
                        results.append(SimpleNamespace(
                            device=port,
                            vid=vid,
                            description=desc or "USB Serial Device (%s)" % port,
                            interface=None,
                            hwid=hwid0,
                            location="",
                            _mi=mi_n,
                        ))
                finally:
                    winreg.CloseKey(inst)
        finally:
            winreg.CloseKey(root)
        return results

    def find_light_port(vids=XIAO_VIDS):
        """Windows 路径:枚举注册表 COM 口,VID 过滤 + _select_data_port 判定。"""
        explicit = os.environ.get(ENV_PORT)
        if explicit:
            return explicit

        matches = [p for p in _enumerate_usb_ports()
                   if p.vid is not None and p.vid in vids]
        return _select_data_port(matches)

    def send_command(port, byte, timeout=1.0):
        """Windows 路径:ctypes 打开 COM 口写单字节。`byte` 为单字节 bytes。"""
        path = "\\\\.\\" + port
        h = kernel32.CreateFileW(path, GENERIC_READ | GENERIC_WRITE, 0, None,
                                 OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, None)
        if h == INVALID_HANDLE:
            raise OSError(ctypes.get_last_error(), f"open {port} failed")
        try:
            to = _COMMTIMEOUTS(100, 100, 0, int(timeout * 1000), 0)
            kernel32.SetCommTimeouts(h, ctypes.byref(to))
            kernel32.EscapeCommFunction(h, SETDTR)
            wbuf = ctypes.create_string_buffer(byte)
            n = wt.DWORD(0)
            ok = kernel32.WriteFile(h, wbuf, 1, ctypes.byref(n), None)
            if not ok:
                raise OSError(ctypes.get_last_error(), f"write {port} failed")
            if n.value != 1:
                raise OSError(f"write {port}: only {n.value} byte written")
        finally:
            try:
                kernel32.EscapeCommFunction(h, CLRDTR)
            finally:
                kernel32.CloseHandle(h)

else:
    find_light_port = _find_light_port_generic


COMMANDS = {"on": b"1", "off": b"0", "wait": b"2"}


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    if not argv or argv[0] not in COMMANDS:
        return 0
    debug = os.environ.get("MC_LIGHT_DEBUG") == "1"
    try:
        port = find_light_port()
        if port is None:
            if debug:
                print("mc-light: 未找到 XIAO RP2040 串口", file=sys.stderr)
            return 0
        send_command(port, COMMANDS[argv[0]])
    except Exception as e:
        # 作为 hook 被调用时不要吵闹地失败;设 MC_LIGHT_DEBUG=1 可以打印错误定位问题。
        if debug:
            print(f"mc-light: {type(e).__name__}: {e}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
