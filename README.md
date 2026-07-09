# mc-light

感知 Claude Code agent 状态的麦当劳金拱门 "M" 指示灯。agent 干活时 M 亮金色,空闲时熄灭。USB 连接,跨平台(Windows / Ubuntu)。

## 硬件

- Seeed XIAO RP2040 ×1(板载 NeoPixel RGB 灯)
- USB-C 数据线 ×1(必须是数据线,非纯充电线)
- 3D 打印:半透明金拱门 M 外壳(约 6cm)+ 底座,PLA 半透明/白色。M 罩在板载灯珠上方,靠打印件壁厚做光线漫射。

## 安装

### 1. 固件(板子端)
1. 给 XIAO RP2040 刷 CircuitPython。
2. 把 `neopixel.mpy` 放进 `CIRCUITPY/lib/`。
3. 复制 `firmware/boot.py`、`firmware/code.py` 到 `CIRCUITPY` 根目录,重新插拔。

### 2. 主机脚本(电脑端)
```
pip install -r host/requirements.txt
```
自测:`python3 host/mc_light.py on`(不插灯也应静默退出、返回 0)。

### 3. Claude Code hooks
把 `hooks/settings.ubuntu.json`(Ubuntu)或 `hooks/settings.windows.json`(Windows)的内容合并进 `~/.claude/settings.json`,并把命令里的路径改成你的绝对路径。Windows 用 `python`,Ubuntu 用 `python3`。

## 工作原理

```
Claude Code 事件 → hook 脚本 → USB 串口(单字符 1/0)→ XIAO 固件 → RGB 灯
```

- `UserPromptSubmit` → 发 `1`(亮金色)
- `Stop` → 发 `0`(灭)
- 脚本按 USB VID `0x2E8A` 自动找设备,不硬编码端口名。
- 找不到灯或出错时脚本静默退出,绝不影响 Claude Code。
- 固件 10 分钟看门狗:若 Claude 异常退出未发 `0`,灯会自动熄灭。

## 验收

插上灯用 Claude Code:发一句话 → M 亮金色;答完 → M 灭。不插灯时 Claude Code 完全正常。
