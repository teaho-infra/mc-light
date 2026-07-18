# mc-light

感知 Claude Code agent 状态的麦当劳金拱门 "M" 指示灯。agent 干活时 M 常亮金色,等待授权时闪烁,空闲时熄灭。USB 连接,跨平台(Windows / Ubuntu)。

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
Claude Code 事件 → hook 脚本 → USB 串口(单字符 1/2/0)→ XIAO 固件 → RGB 灯
```

- `UserPromptSubmit` → 发 `1`(常亮金,干活中)
- `Notification`(需要授权)→ 发 `2`(金色闪烁,等待授权)
- `PostToolUse`(工具执行完,含授权后)→ 发 `1`(恢复常亮)
- `Stop` → 发 `0`(灭,空闲)
- 脚本按 USB VID 自动找设备(同时匹配 Raspberry Pi 官方 `0x2E8A` 与 Seeed 自家 `0x2886`),不硬编码端口名。
- 找不到灯或出错时脚本静默退出,绝不影响 Claude Code。
- 固件 45 秒看门狗:常亮或闪烁超时未更新自动熄灭(兜住 Ctrl+C 中断,因为 Claude Code 中断不触发 Stop hook)。

## 验收

插上灯用 Claude Code:发一句话 → M 常亮金;触发需要授权的操作 → M 闪烁;点允许 → M 恢复常亮;答完 → M 灭。不插灯时 Claude Code 完全正常。

## 排错

脚本作为 hook 时默认静默失败,不会吵到 Claude Code。手动排查加环境变量:

```
MC_LIGHT_DEBUG=1 python3 host/mc_light.py on
```

出错会打到 stderr。常见两坑:

### Ubuntu:`Permission denied: '/dev/ttyACM*'`

`/dev/ttyACM*` 属 `root:dialout`,普通用户默认没这个组。修复:

```
sudo usermod -aG dialout $USER
```

**必须重新登录一次**(注销再登录,或重启),`groups` 里才会出现 `dialout`,当前 shell 里不重登怎么试都还是 permission denied。Windows 没这个问题。

### 找不到设备 / VID 不匹配

Seeed 版 XIAO RP2040 的 USB VID 是 `0x2886`,不是 Raspberry Pi 官方的 `0x2E8A`。脚本现在两个 VID 都匹配。如果是别家 RP2040 板子(VID 不在这两个里),用下面命令看真实 VID,再加到 `host/mc_light.py` 的 `XIAO_VIDS`:

```
python3 -c "from serial.tools import list_ports; [print(p.device, hex(p.vid) if p.vid else None, p.description) for p in list_ports.comports()]"
```

如果看到板子只出一个 `ttyACM`(应该有两个:控制台 + 数据),说明 `firmware/boot.py` 没生效——检查它是否已复制到 `CIRCUITPY` 根目录并**断电重插**过一次(boot.py 只在上电时执行)。
