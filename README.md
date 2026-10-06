# mc-light

感知 Claude Code agent 状态的麦当劳金拱门 "M" 指示灯。agent 干活时 M 常亮金色,等待授权时闪烁,空闲时熄灭。USB 连接,跨平台(Windows / Ubuntu)。

## 效果

| agent 状态 | 灯效 |
|---|---|
| 干活中(用户提交 / 工具执行完) | 金色常亮 |
| 等待授权(Notification) | 金色闪烁(亮 0.5s / 灭 0.5s) |
| 空闲(Stop / SessionEnd) | 熄灭 |

## 项目结构

```
mc-light/
├── firmware/            # XIAO RP2040 端 CircuitPython 固件
│   ├── boot.py          # 开启第二路 USB CDC 数据串口
│   └── code.py          # 主循环:读串口单字符,驱动 NeoPixel,45s 看门狗
├── host/                # 电脑端脚本
│   ├── mc_light.py      # hook 入口:按 VID 找串口,发送命令字符
│   ├── requirements.txt # 依赖(pyserial)
│   └── tests/           # pytest 单元测试(find_light_port / main 等)
├── hardware/            # 3D 打印外壳
│   ├── generate_m_shell.py  # 参数化生成显示器侧贴灯盒 STL
│   ├── test_generate_m_shell.py
│   └── *.stl / *.3mf    # 生成的打印件与切片文件
├── hooks/               # Claude Code hooks 配置样例
│   ├── settings.ubuntu.json
│   └── settings.windows.json
├── docs/                # 设计文档与迭代方案(superpowers specs/plans)
├── server.sh            # 辅助脚本
└── README.md
```

## 硬件

- Seeed XIAO RP2040 ×1(板载 NeoPixel RGB 灯)
- USB-C 数据线 ×1(必须是数据线,非纯充电线)
- 3D 打印:显示器右侧贴装方形灯盒。后壳容纳 XIAO RP2040,USB-C 从底部往上插入;前盖用红色半透明区域 + 黄色半透明 M 区域多色打印,两者正面齐平并透光。

### 3D 打印件

`hardware/generate_m_shell.py` 生成显示器侧贴灯盒:

| 文件 | 用途 |
|---|---|
| `hardware/mc_light_monitor_back.stl` | 后壳,背面贴双面胶,内部放 XIAO RP2040 |
| `hardware/mc_light_monitor_front_red.stl` | 前盖红色半透明区域 |
| `hardware/mc_light_monitor_front_M.stl` | 前盖黄色半透明 M 区域 |
| `hardware/mc_light_monitor_front_assembled.stl` | 前盖红黄区域装配预览 |
| `hardware/mc_light_monitor_assembled.stl` | 整体装配预览 |

多色打印时,把红色区域和黄色 M 区域作为同一个前盖的两个颜色对象合并打印。前盖正面齐平,M 不突出。装配时将 XIAO RP2040 放进后壳,USB-C 端朝下,确认线缆能从底部向上插入,再扣上前盖并把后壳贴到显示器右侧。

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
- `Stop` / `SessionEnd` → 发 `0`(灭,空闲)

### 通信协议

主机与板子之间只有单字节字符命令,无握手、无回包:

| 字符 | 含义 | 固件行为 |
|---|---|---|
| `1` | 常亮 | 金色 (255, 180, 0) 常亮 |
| `2` | 闪烁 | 金色以 0.5s 半周期闪烁 |
| `0` | 熄灭 | 关灯 |
| 其它 | 预留(3-9) | 忽略 |

### 关键设计

- **串口选择**:`boot.py` 用 `usb_cdc.enable(console=True, data=True)` 打开两路 CDC,系统枚举出两个 ttyACM。`host/mc_light.py` 的 `find_light_port()` 按 description 里的 "CDC2" 选中数据口,选不到再回退到序号更大的那个。
- **VID 自动匹配**:同时匹配 Raspberry Pi 官方 `0x2E8A` 与 Seeed 自家 `0x2886`,不硬编码端口名;别家 RP2040 板子可把 VID 加进 `XIAO_VIDS`。
- **失败静默**:找不到灯或出错时脚本静默退出、返回 0,绝不影响 Claude Code(`MC_LIGHT_DEBUG=1` 时才把错误打到 stderr)。
- **45 秒看门狗**:固件侧常亮或闪烁超时未更新自动熄灭——兜住 Ctrl+C 中断(Claude Code 中断不触发 Stop hook)。
- **非阻塞读**:固件 `serial.timeout = 0`,主循环 50ms 一拍,同时处理闪烁翻转与看门狗。

## 测试

```
pytest host/tests
pytest hardware/test_generate_m_shell.py
```

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
