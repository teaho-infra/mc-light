# 麦当劳 M 标志重新设计教程

> 给小白的、从零开始的、用 FreeCAD 或 Blender 重新设计 mc-light 显示器侧贴 M 灯标志的指引

## 0. 你为什么会看到这份文档

`mc-light/hardware/mc_light_monitor_front_M.stl` 是**程序化生成**的 M 标志(用 Python + shapely + trimesh 算出贝塞尔曲线)。当前默认参数(M_WIDTH=24, LEG_H=12, ARCH_R=6)产生的 M 比例是 **24mm 宽 × 21.5mm 高(1.12:1)**,太瘦、太尖锐、腿短。

**真实麦当劳金拱门 M 的宽高比 ≈ 1.3:1**(参考官网 logo 规范和 Wikipedia),即 24mm 宽应当对应 18-19mm 高,而且:
- 拱的弧度更平缓(不是尖锐抛物线)
- 腿更短(脚不落地或浅落地)
- 笔画的"中央 V 形"角度更大、更圆润

这份教程**不改** `generate_m_shell.py` 也不改 STL,**教你从零画一个**几何上更接近真标的 M 标志,然后**替换** `mc_light_monitor_front_M.stl`。

## 1. 准备

### 1.1 工具(任选一个,二选一)

| 工具 | 适合谁 | 安装 | 体量 |
|---|---|---|---|
| **FreeCAD 1.0** | 想精确参数化、要走 Part Design 工作流、能用 Python 脚本 | `sudo apt install freecad` 或 `conda install -c conda-forge freecad` | ~500MB |
| **Blender 4.x** | 习惯 Blender、想直观捏模型、要先预览切片 | `sudo apt install blender` 或 https://blender.org/download | ~300MB(已装在 `/usr/bin/blender`) |

**推荐:FreeCAD 主画 + Blender 验证**。

### 1.2 关键参考

1. **McDonald’s 官方品牌资源**:
   - 搜索 "McDonald's Golden Arches brand guidelines" 看真标比例
   - 维基百科:https://en.wikipedia.org/wiki/McDonald%27s_(wordmark) 的 "Logo" 章节
2. **几何规范(常用参考)**:
   - 整个 M 宽 24mm,高 18mm(宽高比 1.33:1)
   - 腿宽(底端笔画粗)≈ 3.5mm
   - 中央 V 形底端点(最深处)y ≈ -2mm(在 M 几何中心之下)
   - 拱顶最高点 y ≈ 9mm
3. **最终尺寸**(你最终要导出的 STL):
   - 宽 24mm × 高 18mm × 厚 1.2mm(跟灯盒 `FRONT_T=1.2mm` 匹配)

## 2. 方法 A:FreeCAD(推荐)

### 2.1 启动 + 切换工作台

1. 终端:`freecad` (或 `freecad &` 后台)
2. **菜单 → 工作台 → Part Design**(图标是蓝色立方体带斜线)
3. **视图 → 视图 → Standard / Orthographic**(正视,正交投影)
4. 鼠标:中键拖动旋转,Shift+中键平移,滚轮缩放

### 2.2 画 M 草图(Sketcher)

**步骤 1:创建 Body**
- 工具栏 → `Create body`(一个空 Body 出现在树里)
- 选中 Body → `Create sketch` → 选 **XY 平面**
- 进入 Sketcher 工作台

**步骤 2:画 M 的 6 个关键点**

按真实麦当劳比例,在草图里画以下 6 个点(原点 0,0 = M 几何中心):

```
       P3 ( -3.6,  9.0 )              P4 ( 3.6, 9.0)        ← 拱顶
        ╱ ── ── ── ── ── ── ╲      ╱
       ╱                       ╲  ╱
      ╱                          ╲╱
P1 (-12, -9)  P5 (-3.6, -2)  P2 (0, -2)  P6 (3.6, -2)  P7 (12, -9)   ← 脚
└── 左腿 ──┘  └── 左 V 边──┘ └ 中┘ └── 右 V 边──┘  └── 右腿 ──┘
```

**操作**:
- 工具栏选 `Create point`(点工具)
- 在草图区点击放 7 个点(P1..P7,顺序:左下脚→左拱起→中 V 左→中 V 右→右拱起→右下脚,**M 是连续一笔画**)
- 点位置输坐标(选点 → 左下角属性面板改 X/Y,或 F2 编辑):
  - P1: (-12, -9)
  - P3: (-3.6, 9.0) ← 左拱顶
  - P5: (-3.6, -2) ← 左 V 底
  - P2: (0, -2) ← V 最低点(中央)
  - P6: (3.6, -2) ← 右 V 底
  - P4: (3.6, 9.0) ← 右拱顶
  - P7: (12, -9)

> 7 个点 P1..P7 是 M 的关键"骨架"点。M 实际是 1 条闭合曲线 + 2 个矩形(腿填充),但 FreeCAD 草图先从点开始,再用 B-Spline 连。

**步骤 3:用 B-Spline 把点连成 M 形状**

- 工具栏 `Create B-spline`(贝塞尔曲线工具)
- 从 P1 开始,依次点击 P3, P2, P4, P7(让 spline 穿过这 5 个点)
- 闭合:spline 末尾再点一次 P1
- 这是 M 的**中线**(一根线)

> ⚠️ 如果 P1→P3→P2→P4→P7 这条线在 P2 拐弯太尖锐,选中 spline → 控制点模式 → 拖 P2 的两个控制柄让 V 形更圆润。

**步骤 4:腿的宽度(关键!)**

麦当劳 M 的腿是**有厚度的**,不是你刚画的中线。两种做法:

**做法 1:用 Offset(推荐)**
- 工具栏 `Create offset`
- 选刚才的 spline
- 偏移距离 = `1.75` mm(半个腿宽)
- 方向:向外(远离中线)
- 现在有了 2 条平行 spline(中线 + 外缘)

**做法 2:用 Width Constraint(简单)**
- 不画 spline,直接在草图里画**两个矩形** + **两个圆弧**,M 是 4 个独立几何拼的:
  - 左腿:矩形 (-12.0, -9) → (-8.5, 0),长 19mm 宽 3.5mm
  - 左拱:圆弧从 (-8.5, 0) 弯到 (-3.6, 9),半径 ≈ 10
  - 中 V:三角形 / 圆弧拼,顶点 (0, -2)
  - 右拱、右腿:镜像左半

教程主推**做法 1**(平滑好看),但**做法 2 更适合新手**。

**步骤 5:验证闭合**
- 工具栏 `Validate sketch`(对勾图标)
- 草图必须**闭合**(否则无法 Pad 拉伸)
- 红线 = 缺约束(可选,新手不强制)

### 2.3 拉伸成 3D

1. 退出 Sketcher(点 `Leave sketch` 或 `Done`)
2. 选中刚才的 sketch
3. 工具栏 `Pad` 工具
4. 长度: `1.2 mm`(跟 `FRONT_T` 匹配,黄色区域厚度)
5. 方向:对称(默认向上)
6. OK → 现在你有一个 24×18×1.2mm 的 M 标志 3D 模型

### 2.4 导出 STL

1. 选中 Body(或 Pad)
2. **菜单 → File → Export...**
3. 格式选 `STL mesh (.stl)`
4. 命名:`mc_light_monitor_front_M.stl`
5. 路径:`/home/leonbook5/IdeaProjects/agentspace/mc-light/hardware/`
6. **替换**已有文件(可以先备份: `cp ... .../mc_light_monitor_front_M.stl.bak`)
7. **Export → 选 ASCII 或 Binary**(Binary 体积小 4-5 倍,推荐)

### 2.5 验证 STL 尺寸

```bash
# conda 装 trimesh
conda install -c conda-forge trimesh
# 或 pip
pip install trimesh

# 检查尺寸
python3 -c "
import trimesh
m = trimesh.load('/home/leonbook5/IdeaProjects/agentspace/mc-light/hardware/mc_light_monitor_front_M.stl')
b = m.bounds
print(f'宽: {b[1][0]-b[0][0]:.2f}mm  (期望 24)')
print(f'高: {b[1][1]-b[0][1]:.2f}mm  (期望 18)')
print(f'厚: {b[1][2]-b[0][2]:.2f}mm  (期望 1.2)')
"
```

## 3. 方法 B:Blender(更直观)

### 3.1 启动 + 设单位

```bash
blender  # 或 blender file.blend 后台
```

**关键设置(改 STL 默认单位到 mm)**:
- 菜单 `Edit → Preferences → Scenes → Unit Scale`
- Length: `Millimeters`
- 关闭 `Separate Units` 改 `Metric`
- 这是 Blender 4.x 改单位的地方,不同版本路径可能略不同

### 3.2 画 M 标志

**方法 1(新手):用 SVG 导入**

1. 浏览器打开 https://en.wikipedia.org/wiki/McDonald%27s
2. 找一个 SVG 格式的 M logo(右键 → 另存为 → `.svg`)
3. Blender:`File → Import → Scalable Vector Graphics (.svg)`
4. 选刚才的 svg
5. SVG 会作为 Curve 导入,**编辑模式**(Tab) 选中所有顶点,`S` 缩放到 24mm 宽
6. **Properties → Object Data → Geometry → Extrude: 0.0012**(1.2mm 厚,单位 Blender 内部是 m,所以写 0.0012)

**方法 2(进阶):用 Grease Pencil / Bézier 画**

1. 删默认 cube
2. `Add → Curve → Bézier`
3. Tab 进入编辑模式
4. 像 FreeCAD 那样画 7 个控制点(同 §2.2 的 P1..P7 坐标)
5. 闭合:`右键 → Toggle Cyclic` 或菜单 `Curve → Make Cyclic`
6. **Object Data Properties → Geometry → Extrude: 0.0012 m**

**方法 3(老手):用 Python 脚本(对应 generate_m_shell.py 思路)**

在 Blender 的 Scripting 工作台:

```python
import bpy
import math

# 清空场景
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# 7 个控制点(单位 m,因为 Blender 内部是 m)
scale = 0.001  # 1mm = 0.001 m
P = {
    'P1': (-12*scale, -9*scale, 0),
    'P3': (-3.6*scale, 9*scale, 0),
    'P5': (-3.6*scale, -2*scale, 0),
    'P2': (0, -2*scale, 0),
    'P6': (3.6*scale, -2*scale, 0),
    'P4': (3.6*scale, 9*scale, 0),
    'P7': (12*scale, -9*scale, 0),
}

# 创建 Bézier 曲线
curve_data = bpy.data.curves.new('M_Curve', type='CURVE')
curve_data.dimensions = '2D'
spline = curve_data.splines.new(type='BEZIER')

# 7 个点
points = ['P1', 'P3', 'P2', 'P4', 'P7']  # M 的中线(简化)
spline.bezier_points.add(len(points) - 1)
for i, name in enumerate(points):
    bp = spline.bezier_points[i]
    bp.co = P[name]
    bp.handle_type_left = 'AUTO'
    bp.handle_type_right = 'AUTO'

# 闭合
spline.use_cyclic = True

# 挤出 1.2mm 厚
curve_data.extrude = 1.2 * scale

# 加到场景
obj = bpy.data.objects.new('M_Logo', curve_data)
bpy.context.collection.objects.link(obj)
```

F3 搜 `export` → `STL` → 选这个对象导出。

### 3.3 导出 STL

1. 选中 M 对象
2. `File → Export → Stl (.stl)`
3. **Transform → Scale: 1.0**(不要乱改)
4. **Geometry → Export: Selected Objects**(只导出 M,不要 cube 等)
5. 文件名:`mc_light_monitor_front_M.stl`
6. 覆盖 `~/IdeaProjects/agentspace/mc-light/hardware/` 原文件

## 4. 用 Blender 切片预览(可选)

如果你要送到 3D 打印机,**强烈建议**用 Blender 的切片插件预览:

1. Blender: `Edit → Preferences → Add-ons`
2. 搜索 `切片` 或 `PrusaSlicer` 之类的 addon,启用
3. 选中 M 对象 → 切片预览
4. 检查:
   - 壁厚 ≥ 0.8mm(0.4mm 喷嘴最小)
   - 桥接无悬空 > 5mm
   - 整体能放进 38×38mm 灯盒(留 7mm 边距)

或者用 **Bambu Studio** / **PrusaSlicer** / **Cura** 直接打开 STL,更专业。

## 5. 跟原 Python 脚本的关系

### 5.1 不需要改 `generate_m_shell.py`

这份教程**不让你改** `generate_m_shell.py`,**只让你替换 STL**。理由:
- `generate_m_shell.py` 是**参数化生成器**,改参数要重装 Python 依赖(shapely, trimesh, manifold3d)
- 手工 FreeCAD/Blender 画出来的 M 更"手工调",适合一次性修正
- 维护 2 套 M 来源(程序 + 手工)比只保留 1 套手工的更灵活

### 5.2 如果你以后想回到程序化路线

新 M 的参数可以是:
- `M_WIDTH = 24.0`(不变)
- `ARCH_R = 7.0`(原 6.0,稍大)
- `LEG_H = 10.0`(原 12.0,稍短)→ `M_HEIGHT = 17.0`
- `M_WIDTH / M_HEIGHT` = 1.41(更接近真标 1.3~1.5)

要改,改 `hardware/generate_m_shell.py` 的 4 个参数(行 43-46),重跑:
```bash
cd ~/IdeaProjects/agentspace/mc-light/hardware
python3 generate_m_shell.py
```

**但** 调整贝塞尔曲线的 12 个控制点(行 102-130)更关键 — 那是 M "好不好看"的灵魂。新手改控制点会乱,推荐 FreeCAD 手工。

## 6. 验收清单

导出新 STL 后,**强制**过这些检查:

```bash
# 1. 尺寸对吗
python3 -c "
import trimesh
m = trimesh.load('/home/leonbook5/IdeaProjects/agentspace/mc-light/hardware/mc_light_monitor_front_M.stl')
b = m.bounds
w = b[1][0]-b[0][0]
h = b[1][1]-b[0][1]
t = b[1][2]-b[0][2]
print(f'宽 {w:.2f}mm 期望 24.0 ±0.5')
print(f'高 {h:.2f}mm 期望 18.0 ±0.5  (重要!原来 21.5 太瘦)')
print(f'厚 {t:.2f}mm 期望 1.2 ±0.1')
print(f'宽高比: {w/h:.2f} 期望 1.30~1.50')
assert 23.5 <= w <= 24.5, '宽度不在 24±0.5'
assert 17.5 <= h <= 18.5, '高度不在 18±0.5'
assert 1.1 <= t <= 1.3, '厚度不在 1.2±0.1'
assert 1.30 <= w/h <= 1.50, '宽高比不对'
print('✅ 全部通过')
"
```

如果通过,新 M 标志就**几何合规**。然后:
1. **视觉验收**:在 FreeCAD/Blender 里转一圈,看 M 像不像
2. **打印验证**:送切片软件看能不能印
3. **装上灯盒看效果**:打印出来后,装上 XIAO RP2040,通电看 M 透光效果

## 7. 故障排查

### 7.1 FreeCAD 草图无法 Pad

**症状**:Pad 按钮灰的 / 报错 "Sketch is not closed"

**解**:
- 选草图 → 编辑 → 看有没有"开口"(红线)
- 闭合:用 `Create line` 工具手动把最后一点连回第一点
- 或者 spline 末点右键 → `Make cyclic`

### 7.2 Blender 单位错了

**症状**:导出 STL 后尺寸是 24 米而不是 24mm

**解**:
- `Scene Properties → Units → Unit Scale = 0.001`
- 或 Transform → Apply Scale 1.0
- 改完**重新导出**

### 7.3 STL 表面有破洞

**症状**:切片软件报错 "non-manifold edges"

**解**:
- FreeCAD:用 `Part → Refine shape` 修复
- Blender:进入编辑模式 → `Mesh → Clean up → Merge by Distance`(0.0001)
- 实在不行,导出时勾 `Apply modifiers`

### 7.4 M 看起来不对(瘦 / 胖 / 歪)

**调整坐标**:
- 太瘦 → 把 P3 / P4 的 y 减小(从 9 → 7)
- 太胖 → 把 P1 / P7 的 y 增大(从 -9 → -10)
- 拱太尖 → P3 / P4 的 y 减小,或拉 spline 控制柄
- 脚太长 → P1 / P7 的 y 减小(从 -9 → -7)
- 改完重画,回到 §6 跑验收

## 8. 推荐学习路径(小白)

1. **第 1 天**:FreeCAD Part Design 入门
   - 官方教程:https://wiki.freecad.org/Part_tutorial
   - 跟着画个立方体+倒角,**会了再回来**
2. **第 2 天**:FreeCAD Sketcher 画二维
   - 教程:https://wiki.freecad.org/Sketcher_tutorial
   - 画几个矩形、圆、B-spline
3. **第 3 天**:本教程 §2.1-2.4,画第一个 M,导出
4. **第 4 天**:切片 + 打印(可选,先电子版验)
5. **后续**:用 Blender 改 / 优化,做动画版 M(可选)

**总投入**:**2-4 小时**能完成第一个新 M 标志(纯软件验证),打印出来 + 装灯 + 通电看效果再 +1-2 天(含等打印)。

## 9. 致谢

这份教程参考了:
- McDonald's 品牌规范(公开资料)
- FreeCAD 官方 Sketcher 教程
- Blender 4.x 手册
- 你原 `hardware/generate_m_shell.py` 的几何参数(了解灯盒尺寸上下文)
