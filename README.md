# 裂谷竞技 · ARENA

> 俯视角波次射击：单人对抗机器人波次，扛住尽可能多的波。

用 [Zan](https://github.com/joyspinch/zan-lang) 语言写的独立游戏项目（仓库根自带 git 仓库）。完整设计与实现说明见 [`PROJECT.md`](PROJECT.md)。

## 玩法

- **目标**：撑过尽可能多的波次。玩家 HP 归零即本局结束，进入结算。
- **地图**：960×600 竞技场，四周 22 像素墙，中部 5 处掩体（可挡子弹、挡人）。
- **玩家**：100 HP、初始 60 发弹药（上限 99）、冲刺耐力槽。
- **敌人**（每种都有独立位图与行为）：

| 兵种 | 解锁波次 | 血量 | 行为 | 接触伤害 |
|------|----------|------|------|----------|
| 冲锋兵 | 第 2 波起（第 1 波教学波全是它） | 30 | 直线追踪，快（118 px/s） | 8 |
| 炮塔 | 第 4 波起 | 55 | 缓慢逼近到 260 像素射程内，然后定点开火（1.7 秒一发） | 6 |
| 重装兵 | 第 6 波起 | 120 | 慢速压上（46 px/s），血厚 | 22 |

- **波次**：第 N 波生成 `2 + N` 个敌人（上限 20）。第 1 波是教学波（清一色
  冲锋兵），之后按解锁波次混编。
- **补给期**：一波清空后有 3 秒补给期——弹药补满、恢复 25 HP、耐力回满，
  然后开下一波。
- **掉落**：每次击杀掉一个弹药箱（+12~20 发），35% 概率额外掉一个医疗包
  （+20 HP），走过去拾取。
- **结算**：到达波数、击杀数、命中率、最高连杀、用时、得分。
- **成长**：最高波数 / 最高分 / 最高连杀 / 局数写进存档，菜单与结算面板可见。

| 操作 | 按键 |
|------|------|
| 移动 | `W` `A` `S` `D` 或方向键（带加速度与摩擦，不是瞬时速度） |
| 瞄准 | 鼠标 |
| 射击 | 鼠标左键，或空格（朝当前瞄准方向） |
| 冲刺 | `Shift`（耗耐力槽，耗尽后停手 0.45 秒开始回耐力） |
| 设置 | `Esc`（音效 / 难度 / 自动驾驶） |

## 构建

需要 [zan-lang](https://github.com/joyspinch/zan-lang) 仓库（`zanc` 编译器、公共包与 stdlib 都在里面）：

```powershell
git clone https://github.com/joyspinch/zan-lang.git
$env:ZAN_HOME = 'D:/path/to/zan-lang'   # 指到刚克隆的 zan-lang 仓库根

pwsh -File client/tools/build.ps1
```

产物：`build/arena/Arena.exe`（运行目录要带上它旁边的 `assets/` 与 `skins/`）。

## 运行

```powershell
cd build/arena
.\Arena.exe
```

## 测试

```powershell
pwsh -File client/tools/test.ps1
```

## 目录结构

```
arena/
client/
  src/      # 游戏源码（.zan 源码 + HTML 界面设计稿）
  assets/   # 位图 / 音频素材
  data/     # 数值表与数据文件
  tests/    # 玩法断言用例
  tools/    # 构建与测试脚本
PROJECT.md
```

## 素材与授权

- 素材清单与授权说明见 [`client/ASSETS.md`](client/ASSETS.md)。

## 许可

本仓库采用 [MIT 许可](LICENSE)。依赖的 zan-lang 仓库采用 ZCSL（Zan Community Source License 1.0）。

## 更多文档

- [`PROJECT.md`](PROJECT.md) —— 完整设计与实现说明
- [`client/ASSETS.md`](client/ASSETS.md) —— 素材清单
