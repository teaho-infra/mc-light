# mc-light 等待授权闪烁(第三态)Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 给 mc-light 增加第三态"等待授权=金色闪烁",授权后恢复常亮,回合结束熄灭。

**Architecture:** 沿用现有三段架构(Claude Code hook 短命脚本 → 单字符 USB 串口 → CircuitPython 固件自持状态)。新增协议字符 `2`=闪烁;固件引入 `OFF/SOLID/BLINK` 模式并在主循环里自持闪烁节奏;主机脚本 `COMMANDS` 增加 `wait`→`2`;hook 配置新增 `Notification`(发 `2`)与 `PostToolUse`(发 `1` 恢复常亮)。

**Tech Stack:** Python 3 + pyserial(主机端,pytest 测试);CircuitPython + neopixel(固件端,硬件手动测试);JSON(hook 配置)。

## Global Constraints

- 协议为单字符 ASCII:`0`=灭,`1`=常亮金,`2`=闪烁;未知字符固件必须忽略、不崩溃(向前兼容)。
- 金色 = `(255, 180, 0)`(固件中常量 `GOLD`)。
- 闪烁节奏:亮 0.5s / 灭 0.5s(周期 1s),硬切换、非渐变。
- 看门狗 = 10 分钟(`WATCHDOG_SECONDS = 600`);SOLID 与 BLINK 都受其管辖。
- hook 脚本必须永远快速、静默、返回码 0,绝不干扰 Claude Code;灯设备缺失/失败一律静默退出。
- 主机脚本发现设备按 USB VID `0x2E8A`,不硬编码端口名。
- 跨平台:Ubuntu 用 `python3`,Windows 用 `python`;`host/mc_light.py` 两平台同一份。
- 测试从 `host/` 目录运行 `python3 -m pytest`(conftest 把 `host/` 加入 sys.path)。

---

### Task 1: 主机脚本新增 `wait` 命令

**Files:**
- Modify: `host/mc_light.py:18`(`COMMANDS` 字典)
- Test: `host/tests/test_mc_light.py`

**Interfaces:**
- Consumes: 现有 `mc_light.COMMANDS`(dict[str, bytes]),`mc_light.main(argv)`。
- Produces: `mc_light.COMMANDS["wait"] == b"2"`;`main(["wait"])` 在找到设备时调用 `send_command(port, b"2")`,无设备/异常时返回 0。

- [ ] **Step 1: Write the failing tests**

在 `host/tests/test_mc_light.py` 末尾追加:

```python
def test_commands_map_wait():
    assert mc_light.COMMANDS["wait"] == b"2"


def test_main_sends_two_for_wait_when_device_found():
    with mock.patch.object(mc_light, "find_light_port", return_value="COM3"), \
         mock.patch.object(mc_light, "send_command") as send:
        assert mc_light.main(["wait"]) == 0
        send.assert_called_once_with("COM3", b"2")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd host && python3 -m pytest tests/test_mc_light.py::test_commands_map_wait tests/test_mc_light.py::test_main_sends_two_for_wait_when_device_found -v`
Expected: FAIL(`KeyError: 'wait'`)

- [ ] **Step 3: Add `wait` to COMMANDS**

把 `host/mc_light.py` 的 `COMMANDS` 改为:

```python
COMMANDS = {"on": b"1", "off": b"0", "wait": b"2"}
```

- [ ] **Step 4: Run full host test suite to verify pass**

Run: `cd host && python3 -m pytest -v`
Expected: PASS(含原有全部用例 + 两条新用例)

- [ ] **Step 5: Commit**

```bash
git add host/mc_light.py host/tests/test_mc_light.py
git commit -m "feat(host): add wait command sending '2' for auth-waiting state"
```

---

### Task 2: 固件新增 BLINK 模式

**Files:**
- Modify: `firmware/code.py`(整段主循环与状态变量)

**Interfaces:**
- Consumes: `GOLD`、`OFF`、`WATCHDOG_SECONDS`、`pixel`、`serial`(现有)。
- Produces: 无被其它任务依赖的接口;这是固件端行为改动。行为契约:收 `1`→常亮金,`2`→闪烁(亮 0.5s/灭 0.5s),`0`→灭;SOLID/BLINK 均受 10 分钟看门狗;未知字符忽略。

> **说明:** 固件运行在 CircuitPython 硬件上(`import board/neopixel/usb_cdc`),无法在开发机跑单元测试。本任务用**硬件手动测试**验证(见 Step 3)。改动集中在状态机与主循环。

- [ ] **Step 1: 用模式状态机重写主循环**

把 `firmware/code.py` 第 26 行起(`last_on = None` 到文件末尾)替换为:

```python
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
```

同时删除原有 `last_on = None` 及其下的旧 `while True` 循环(被上面整体替换)。文件顶部的 imports、`GOLD`/`OFF`/`WATCHDOG_SECONDS` 常量、NeoPixel 电源与初始化、`serial = usb_cdc.data` 部分保持不变。

- [ ] **Step 2: 静态自检(语法与结构)**

Run: `python3 -c "import ast; ast.parse(open('firmware/code.py').read()); print('syntax OK')"`
Expected: 输出 `syntax OK`(仅验证语法;CircuitPython 专有模块无法在开发机导入)

- [ ] **Step 3: 硬件手动测试(把 code.py 拷到 CIRCUITPY 后)**

用串口终端向数据口逐一发送并肉眼确认:
- 发 `1` → 常亮金
- 发 `2` → 金色闪烁(亮约 0.5s、灭约 0.5s)
- 闪烁中发 `1` → 立即转常亮
- 闪烁中发 `0` → 立即灭
- 发未知字符(如 `x`)→ 灯不变、不崩
- (可选)把 `WATCHDOG_SECONDS` 临时改成 `10`,发 `2` 后静置,确认约 10 秒后自动灭;验证完改回 `600`

- [ ] **Step 4: Commit**

```bash
git add firmware/code.py
git commit -m "feat(firmware): add blink mode for auth-waiting (protocol '2')"
```

---

### Task 3: Hook 配置新增 Notification 与 PostToolUse

**Files:**
- Modify: `hooks/settings.ubuntu.json`
- Modify: `hooks/settings.windows.json`

**Interfaces:**
- Consumes: Task 1 的 `mc_light.py wait`(发 `2`)与现有 `on`(发 `1`)。
- Produces: 两份配置示例,各含 `UserPromptSubmit`/`Notification`/`PostToolUse`/`Stop` 四个 hook。

> **说明:** JSON 配置示例,无自动化测试;验证方式为 JSON 合法性 + 人工核对事件映射。

- [ ] **Step 1: 更新 Ubuntu 配置**

把 `hooks/settings.ubuntu.json` 整体替换为:

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          { "type": "command", "command": "python3 /ABSOLUTE/PATH/mc-light/host/mc_light.py on" }
        ]
      }
    ],
    "Notification": [
      {
        "hooks": [
          { "type": "command", "command": "python3 /ABSOLUTE/PATH/mc-light/host/mc_light.py wait" }
        ]
      }
    ],
    "PostToolUse": [
      {
        "hooks": [
          { "type": "command", "command": "python3 /ABSOLUTE/PATH/mc-light/host/mc_light.py on" }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          { "type": "command", "command": "python3 /ABSOLUTE/PATH/mc-light/host/mc_light.py off" }
        ]
      }
    ]
  }
}
```

- [ ] **Step 2: 更新 Windows 配置**

把 `hooks/settings.windows.json` 整体替换为:

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          { "type": "command", "command": "python C:\\ABSOLUTE\\PATH\\mc-light\\host\\mc_light.py on" }
        ]
      }
    ],
    "Notification": [
      {
        "hooks": [
          { "type": "command", "command": "python C:\\ABSOLUTE\\PATH\\mc-light\\host\\mc_light.py wait" }
        ]
      }
    ],
    "PostToolUse": [
      {
        "hooks": [
          { "type": "command", "command": "python C:\\ABSOLUTE\\PATH\\mc-light\\host\\mc_light.py on" }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          { "type": "command", "command": "python C:\\ABSOLUTE\\PATH\\mc-light\\host\\mc_light.py off" }
        ]
      }
    ]
  }
}
```

- [ ] **Step 3: 验证两份 JSON 合法**

Run: `python3 -c "import json; json.load(open('hooks/settings.ubuntu.json')); json.load(open('hooks/settings.windows.json')); print('json OK')"`
Expected: 输出 `json OK`

- [ ] **Step 4: Commit**

```bash
git add hooks/settings.ubuntu.json hooks/settings.windows.json
git commit -m "feat(hooks): add Notification (blink) and PostToolUse (solid) hooks"
```

---

### Task 4: 更新 README

**Files:**
- Modify: `README.md`(工作原理、事件映射、验收)

**Interfaces:**
- Consumes: 上述三态协议与四个 hook 事件。
- Produces: 文档,无测试。

- [ ] **Step 1: 更新"工作原理"事件映射段**

把 `README.md` 中"工作原理"下的事件列表(现为 `UserPromptSubmit → 1` / `Stop → 0` 两条)替换为:

```markdown
- `UserPromptSubmit` → 发 `1`(常亮金,干活中)
- `Notification`(需要授权)→ 发 `2`(金色闪烁,等待授权)
- `PostToolUse`(工具执行完,含授权后)→ 发 `1`(恢复常亮)
- `Stop` → 发 `0`(灭,空闲)
- 脚本按 USB VID `0x2E8A` 自动找设备,不硬编码端口名。
- 找不到灯或出错时脚本静默退出,绝不影响 Claude Code。
- 固件 10 分钟看门狗:常亮或闪烁超时未更新则自动熄灭。
```

- [ ] **Step 2: 更新顶部一句话描述**

把 `README.md` 第 3 行改为:

```markdown
感知 Claude Code agent 状态的麦当劳金拱门 "M" 指示灯。agent 干活时 M 常亮金色,等待授权时闪烁,空闲时熄灭。USB 连接,跨平台(Windows / Ubuntu)。
```

- [ ] **Step 3: 更新"验收"段**

把 `README.md` 末尾"验收"段落正文替换为:

```markdown
插上灯用 Claude Code:发一句话 → M 常亮金;触发需要授权的操作 → M 闪烁;点允许 → M 恢复常亮;答完 → M 灭。不插灯时 Claude Code 完全正常。
```

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: document three-state behavior and new hooks"
```

---

## Self-Review

**1. Spec coverage:**
- 协议 `2`=闪烁 → Task 1(主机)+ Task 2(固件)✓
- 事件映射 `Notification`/`PostToolUse` → Task 3 ✓
- 固件 BLINK 模式 + 看门狗纳入 → Task 2 ✓
- 主机 `COMMANDS` 加 `wait` → Task 1 ✓
- README 更新 → Task 4 ✓
- 硬件/3D 打印件/设备发现逻辑不动 → 计划中未触碰,符合非目标 ✓

**2. Placeholder scan:** 无 TBD/TODO;每个代码步骤含完整代码;JSON/固件全文给出。✓

**3. Type consistency:** `COMMANDS["wait"] == b"2"` 在 Task 1 定义、Task 3 引用一致;固件模式字符串 `"off"/"solid"/"blink"` 与 `set_mode` 全程一致;`GOLD/OFF/WATCHDOG_SECONDS/BLINK_INTERVAL` 命名一致。✓
