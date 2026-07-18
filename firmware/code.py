# mc-light 固件:读 USB 数据串口的单字符,驱动板载 NeoPixel
import time

import board
import digitalio
import neopixel
import usb_cdc

GOLD = (255, 180, 0)          # 麦当劳金黄色
OFF = (0, 0, 0)
WATCHDOG_SECONDS = 45         # 45 秒兜底熄灭:Ctrl+C 中断后 Stop hook 不触发,靠这个自动熄

# XIAO RP2040 板载 NeoPixel 需要先给 NEOPIXEL_POWER 供电
power = digitalio.DigitalInOut(board.NEOPIXEL_POWER)
power.direction = digitalio.Direction.OUTPUT
power.value = True

pixel = neopixel.NeoPixel(board.NEOPIXEL, 1)
pixel.brightness = 0.5
pixel[0] = OFF                # 上电默认:灭

serial = usb_cdc.data         # 数据口(非 REPL 控制台口)
if serial is not None:
    serial.timeout = 0        # 非阻塞读

# 当前模式:"off" / "solid" / "blink"
mode = "off"
mode_since = time.monotonic()   # 进入当前(非灭)模式的时刻,用于看门狗
blink_on = False                # blink 模式下当前灯是否亮着
last_toggle = time.monotonic()  # 上次翻转时刻
BLINK_INTERVAL = 0.5            # 闪烁半周期:亮 0.5s / 灭 0.5s


def set_mode(new_mode):
    global mode, mode_since, blink_on, last_toggle
    mode = new_mode
    now = time.monotonic()
    if new_mode == "off":
        pixel[0] = OFF
    elif new_mode == "solid":
        pixel[0] = GOLD
        mode_since = now
    elif new_mode == "blink":
        blink_on = True
        pixel[0] = GOLD
        last_toggle = now
        mode_since = now


while True:
    if serial is not None and serial.in_waiting > 0:
        data = serial.read(serial.in_waiting)
        for b in data:
            ch = chr(b)
            if ch == "1":
                set_mode("solid")
            elif ch == "2":
                set_mode("blink")
            elif ch == "0":
                set_mode("off")
            # 其它字符(含预留 3-9)忽略

    now = time.monotonic()

    # 闪烁:按半周期翻转
    if mode == "blink" and (now - last_toggle) >= BLINK_INTERVAL:
        blink_on = not blink_on
        pixel[0] = GOLD if blink_on else OFF
        last_toggle = now

    # 看门狗:solid / blink 超时自动灭
    if mode in ("solid", "blink") and (now - mode_since) > WATCHDOG_SECONDS:
        set_mode("off")

    time.sleep(0.05)
