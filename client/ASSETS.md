# 裂谷竞技 · ARENA —— 资产清单

所有位图与音效都在 `client/assets/` 下，随 exe 一起分发（磁盘优先，
发布后资源在 exe 内嵌表里也能读回）。皮肤包在
`client/assets/skins/arena/skin.css`，构建时另拷一份到 exe 同级的
`skins/arena/`（`Gui.Styling.Skin.Roots` 查的是 exe 同级目录）。

## 位图（22 张，共约 1.2 MB）

### 场景与道具

| 文件 | 入库尺寸 | 显示尺寸 | 用途 | 来源 |
|------|----------|----------|------|------|
| `ground.png` | 960×600（128 色调色板） | 960×600 铺满竞技场 | 竞技场地面（钢板 + 铆钉 + 锈迹） | AI 生成 `gpt-image-2.5` |
| `cover.png` | 184×184 | 84~92 见下 | 掩体（黄黑警示条纹钢制障碍块） | AI 生成 `gpt-image-2.5` |
| `bullet.png` | 28×28 | 14×14 | 子弹（等离子弹头） | AI 生成 `gpt-image-2.5` |
| `explode.png` | 104×104 | 52×52 | 敌人死亡爆炸特效 | AI 生成 `gpt-image-2.5` |
| `ammo.png` | 44×44 | 22×22 | 掉落：弹药箱 | AI 生成 `gpt-image-2.5` |
| `health.png` | 44×44 | 22×22 | 掉落：医疗包 | AI 生成 `gpt-image-2.5` |

掩体的显示尺寸随地图里的掩体矩形走（84/66/92/70/88 像素见
`client/src/ArenaWorld.zan`），位图按矩形等比拉伸。

### 方向精灵表（朝向帧）

引擎运行时转不了图——`Canvas.BlitImage` 只有源矩形 (sx,sy,sw,sh)，没有
旋转、没有水平翻转；`Gui.SpriteBatch` 的每精灵也只有
dx/dy/dw/dh/sx/sy/sw/sh/tint。所以方向帧是**离线烘焙**成精灵表的：一条
横排 PNG，**帧宽 = 帧高**，运行时按角度裁第 n 帧。

| 文件 | 帧数 | 帧边长 | 显示尺寸 | 主体 | 取帧依据 |
|------|------|--------|----------|------|----------|
| `player_sheet.png` | 16 | 112×112 | 56×56 | 玩家（蓝色装甲佣兵） | 瞄准角 `p.aim` |
| `chaser_sheet.png` | 8 | 76×76 | 38×38 | 冲锋兵（红色三角突击无人机） | 朝向玩家 `e.aim` |
| `turret_sheet.png` | 8 | 112×112 | 56×56 | 炮塔（可旋转炮管） | 朝向玩家 `e.aim` |
| `brute_sheet.png` | 8 | 144×144 | 72×72 | 重装兵（重型装甲步行机） | 移动方向 `e.facing` |

**角度 → 帧号的映射（纯函数，`client/src/ArenaFacing.zan`）**

- 精灵表**帧 0 = 主体正面朝上**，之后每帧**顺时针**转 `360 / 帧数` 度
  （玩家 22.5°/帧，其余 45°/帧）。
- 逻辑角用**屏幕坐标**（x 向右 = 0°，y 向下 = +90°），与 `atan2(dy, dx)` 一致。
- 换算成"自上起顺时针"后取**最近帧**：

  ```
  deg   = ((angle * 180 / π) + 90) mod 360      // 自上起顺时针
  step  = 360 / frames
  index = floor((deg + step / 2) / step)         // 四舍五入到最近帧
  index = min(index, frames - 1)
  ```

- 例子（16 帧玩家）：朝上(-π/2)→帧 0，朝右(0)→帧 4，朝下(π/2)→帧 8，
  朝左(π 或 -π)→帧 12；8 帧的敌人：朝上→0、右→2、下→4、左→6。
- 帧界在"自上起顺时针 ±step/2"处，越过帧界归下一帧。
- 映射由 `client/tests/arena_test.zan` 的 `TestFacing()` 钉住（24 条断言：
  边界、±π/±2π 等价、单调递进、玩家 aim 变化 → 帧号变化、炮塔/重装兵
  取帧跟随目标）。

**烘焙脚本**：`client/tools/bake_facing.py`（读 `_scratch/raw/*.png` 原图 →
抠 alpha → 裁到主体 → 绕旋转轴摆进正方画布 → 旋成 N 帧 → 拼横条）。

- 旋转用"**预乘 alpha → 旋转 → 反预乘**"：直接旋转 RGBA 会把透明像素的
  黑色插值进边缘，半透明边缘发黑（黑边）。
- 旋转轴必须与实体在场景里的位置重合：玩家=头盔中心，炮塔=底座圆心，
  冲锋兵=机腹发光眼，重装兵=机身核心。
- 画布边长 = 2×主体最大半径 ×1.04（留 4% 余量，主体落在内切圆里，任意
  角度旋转都不裁角）。
- 冲锋兵原图的机头朝下，烘焙前**预转 180°**，让"帧 0 = 正面朝上"成立。

### UI 底板与投影（程序化生成，非 AI）

`client/tools/bake_ui.py` 用 PIL 画出九宫格可拉伸的底板（切角钢板 +
斜面高光 + 描边）。引擎没有 `border-image`，九宫格在运行时自己切 9 块拼
（`ArenaView.DrawNineSlice`，源矩形在前、目标矩形在后）。

| 文件 | 尺寸 | 切角 | 用途 |
|------|------|------|------|
| `ui_plate.png` / `_hi` / `_down` | 48×36 | 12 | 次要按钮三态（常态/悬停/按下） |
| `ui_plate_primary.png` / `_hi` / `_down` | 48×36 | 12 | 主按钮三态（橙色警示底） |
| `ui_panel.png` | 64×64 | 16 | 面板底板（HUD 面板、结算面板、菜单战绩条） |
| `shadow.png` | 96×48 | — | 椭圆落地投影（软边黑椭圆，压在主体下面） |

### 主体细节

- 玩家/敌人脚下都有**椭圆暗影**（`shadow.png`），主体不再平贴地面。
- 掩体下压一层接触阴影（偏移 5/7 像素的暗块），掩体画在**地面之上、
  角色之下**。
- 受击：主体**抖动**（±2 像素）+ 白色**径向辉光**（引擎没有贴图染色，
  辉光是最接近"闪白"的画法）。死亡：爆炸贴图 + 一圈扩散的冲击波环。

### 旧单张主体图（兜底）

`player.png` / `chaser.png` / `turret.png` / `brute.png` 是上一轮的单张
主体图，保留作**兜底**：精灵表找不到时仍能画出主体（`ArenaView` 里
`xxxSheetPath` 为空才走它们），再找不到才退纯色。

## 音效（8 个，共约 102 KB）

命名 `assets/sfx/<事件>.wav`，22050 Hz 单声道 16bit，全部短于 1 秒，
由 `Game.Foundation.SfxBank` 加载（磁盘优先 + 内嵌兜底 + 限频；没有
声卡时静默失效，游戏照常跑）。

| 文件 | 触发时机 | 合成方式 |
|------|----------|----------|
| `shoot.wav` | 玩家开火（每次命中发射都触发，冷却 40ms） | 880→220 Hz 方波下滑 + 噪声 |
| `hit.wav` | 子弹命中敌人（冷却 30ms） | 1500→900 Hz 正弦"叮" |
| `explode.wav` | 敌人死亡（冷却 60ms） | 低频噪声轰 + 180→45 Hz 三角波 |
| `hurt.wav` | 玩家受伤（被子弹打中或敌人接触，冷却 120ms） | 320→110 Hz 锯齿闷响 |
| `pickup.wav` | 拾取弹药箱 / 医疗包（冷却 60ms） | 880 Hz → 1320 Hz 两声上行 |
| `wave.wav` | 新一波开始 | 392 → 523 → 784 Hz 三音号角 |
| `turret.wav` | 炮塔开火（冷却 90ms） | 240→90 Hz 方波脉冲 |
| `gameover.wav` | 玩家阵亡 | 440 → 330 → 220 Hz 下行三音 |

音效是真被事件调用的（`client/src/ArenaSfx.zan` ← `ArenaGame` 的
开火/命中/爆炸/受伤/拾取/波次/炮塔/阵亡分支），不是加载了从不播。

## 皮肤包（client/assets/skins/arena/skin.css）

科幻工业风：深钢蓝底 + 橙色警示 + 直角硬边。启动时
`host.App().UseSkin("arena")` 应用（**在默认皮肤之后**，否则会被盖回去）。

- `:root` 令牌：`--primary`（警示橙）、`--bg-primary/secondary/tertiary`、
  `--text-primary/secondary/tertiary/inverse`、`--border-primary/secondary/
  hover/focus`、`--divider`、`--shadow-color`、`--border-radius-*`、
  `--radius-*`、`--font-size-*`。
  **注意**：改主题圆角要写 `--border-radius-*`（主题字段名），`--radius-*`
  只在本皮肤自己的规则里生效——两种都写了。
- 规则：`button`（含 `:hover` / `:active` / `:focus` / `.primary` /
  `:disabled`）、`label`、`panel.card` / `card`（设置浮层那张卡）。
- 引擎限制：CSS 背景只吃颜色与线性渐变，**url() 贴图不支持**，也没有
  `border-image`——皮肤是纯色/描边风格，画布上的美术底板走
  `client/assets/ui_*.png`（九宫格自切）。

## 重新出图 / 重新烘焙

原始 1024×1024 生成图在仓库外的 `_scratch/raw/`（不入库）。要重来一遍：

```powershell
# 1) 重新出图（可选）：_scratch/gen.ps1 -Keys player,chaser,turret,brute
# 2) 抠底色 + 裁边 + 缩放：python _scratch/process_assets.py
# 3) 烘焙方向帧：python client/tools/bake_facing.py
# 4) 生成 UI 底板与投影：python client/tools/bake_ui.py
```

`bake_facing.py` / `bake_ui.py` 只依赖 Pillow + numpy，参数见脚本头注释。
