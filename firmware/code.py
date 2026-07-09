# mc-light 固件:读 USB 数据串口的单字符,驱动板载 NeoPixel
import time

import board
import digitalio
import neopixel
import usb_cdc

GOLD = (255, 180, 0)          # 麦当劳金黄色
OFF = (0, 0, 0)
WATCHDOG_SECONDS = 600        # 10 分钟兜底熄灭

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

last_on = None                # 上次点亮时刻;None 表示当前熄灭

while True:
    if serial is not None and serial.in_waiting > 0:
        data = serial.read(serial.in_waiting)
        for b in data:
            ch = chr(b)
            if ch == "1":
                pixel[0] = GOLD
                last_on = time.monotonic()
            elif ch == "0":
                pixel[0] = OFF
                last_on = None
            # 其它字符(含预留 2-9)忽略
    # 看门狗:亮着且超时则自动熄灭
    if last_on is not None and (time.monotonic() - last_on) > WATCHDOG_SECONDS:
        pixel[0] = OFF
        last_on = None
    time.sleep(0.05)
