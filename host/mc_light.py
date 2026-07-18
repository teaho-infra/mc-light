"""mc-light host hook script: send on/off over USB serial to the XIAO RP2040."""
import os
import sys

import serial
from serial.tools import list_ports

# 兼容两种 XIAO RP2040:Raspberry Pi 官方 VID 与 Seeed 自家 VID
XIAO_VIDS = (0x2E8A, 0x2886)


def find_light_port(vids=XIAO_VIDS):
    """Return the device name of the CircuitPython data serial (CDC2), else None.

    boot.py 打开了 console + data 两路 CDC,系统会枚举出两个 ttyACM。
    data 口的 description 里带 "CDC2";按此优先选中,选不到再回退到序号更大的那个。
    """
    matches = [p for p in list_ports.comports() if p.vid in vids]
    if not matches:
        return None
    for p in matches:
        desc = (p.description or "") + " " + (p.interface or "")
        if "CDC2" in desc or "data" in desc.lower():
            return p.device
    # 回退:同一块板子上,data 口通常是排序靠后的那个 ACM
    matches.sort(key=lambda p: p.device)
    return matches[-1].device


COMMANDS = {"on": b"1", "off": b"0", "wait": b"2"}


def send_command(port, byte, timeout=1.0):
    """Open `port`, write `byte`, close. Raises on failure."""
    with serial.Serial(port, timeout=timeout, write_timeout=timeout) as ser:
        ser.write(byte)


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
