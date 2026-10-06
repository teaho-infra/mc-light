# Windows USB 连接适配计划

## 当前结论

项目已有 Windows hook 样例，`pyserial` 也支持 Windows COM 端口，因此通信方案可用于 Windows；但目前不能认为 Windows USB 连接已可靠适配，也没有 Windows 真机验收记录。

主要缺口：

1. `host/mc_light.py` 优先凭端口描述中的 `CDC2`/`data` 找数据口；没有这些文本时，按 `device` 字符串排序并取最后一个。Windows 的两个 CDC COM 号不保证相邻或按 console、data 顺序分配；字符串排序还会把 `COM9` 排在 `COM10` 后。此时可能写入 REPL 控制台口，灯不会响应。
2. 仅按 VID (`0x2E8A`/`0x2886`) 过滤，连接多块同厂商板子时可能选中另一块设备。
3. `hooks/settings.windows.json` 使用占位路径且没有引号；路径含空格时命令可能执行失败。它也缺少与 Ubuntu 样例一致的 `SessionEnd` 熄灯 hook。
4. 现有测试用模拟 COM 口验证基础流程，但没有覆盖 COM 号乱序、描述缺失、多设备、路径含空格，也没有 Windows + XIAO RP2040 实机测试。

## 实施步骤

1. **采集 Windows 枚举信息**：在 Windows 上接入烧录了本项目 `boot.py`/`code.py` 的 XIAO RP2040，运行 `python -m serial.tools.list_ports -v`，记录两路端口的 `device`、VID/PID、`interface`、`description`、`hwid`、`serial_number` 和 `location`。分别验证 Seeed 和 Raspberry Pi VID（若有对应硬件）。
2. **确定数据口识别规则**：优先使用可验证的 USB 接口号或固件设置的独立接口名称，结合 VID/PID、序列号/位置锁定目标板。不要把 COM 号大小当成接口顺序。若元数据不足或有多个候选口，返回“无法确定”，并提供显式端口配置（例如环境变量 `MC_LIGHT_PORT=COM10`）；不要猜测一个口。
3. **修改主机脚本和测试**：让 `find_light_port()` 采用上述规则。补充 COM9/COM10、非连续及反序 COM 号、描述为空、多块板、指定端口不存在等用例。保持 hook 失败时静默返回 0，并在 `MC_LIGHT_DEBUG=1` 下给出候选口和判定原因。
4. **修正 Windows hook 与安装文档**：给 Python 和脚本绝对路径加可靠的命令行引号，添加 `SessionEnd`，说明在 Windows 本机 Python 环境安装 `pyserial`、验证 COM 端口和启用调试的方法。说明 WSL 与 Windows 本机的端口访问需要分别配置。
5. **实机验收**：在 Windows 10/11 上断电重插板子，确认出现 console/data 两个 COM 口；运行 `on`、`wait`、`off`，分别看到常亮、闪烁、熄灭。再通过 Claude Code 触发 `UserPromptSubmit`、`Notification`、`PostToolUse`、`Stop`、`SessionEnd`。重复测试 COM 号变化、路径含空格、无设备及多设备场景，确认不会向 REPL 口写入命令。

## 完成标准

- Windows 真机上自动识别数据口，或在无法唯一识别时用显式端口配置成功连接。
- 所有上述 hook 事件触发正确灯效；断开设备或端口忙时 Claude Code 正常运行。
- Windows 相关自动化测试通过，README 给出可复现的安装、诊断和验收步骤。

参考：[CircuitPython USB CDC 文档](https://docs.circuitpython.org/en/latest/shared-bindings/usb_cdc/)（Windows COM 口顺序不保证）、[pySerial 端口枚举文档](https://pyserial.readthedocs.io/en/latest/tools.html)（端口元数据与顺序）。
