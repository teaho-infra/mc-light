# 启用第二路 USB 串口(数据口),打开它不会复位正在运行的程序
import usb_cdc

usb_cdc.enable(console=True, data=True)
