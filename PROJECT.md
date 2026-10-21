# 裂谷竞技 · ARENA —— 俯视角波次射击

> 仓库外的独立项目（自带 git 仓库）。玩法：单人对抗机器人波次，扛住尽可能多的波。
> 素材清单见 [`client/ASSETS.md`](client/ASSETS.md)。

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

## 怎么玩

| 操作 | 按键 |
|------|------|
| 移动 | `W` `A` `S` `D` 或方向键（带加速度与摩擦，不是瞬时速度） |
| 瞄准 | 鼠标 |
| 射击 | 鼠标左键，或空格（朝当前瞄准方向） |
| 冲刺 | `Shift`（耗耐力槽，耗尽后停手 0.45 秒开始回耐力） |
| 设置 | `Esc`（音效 / 难度 / 自动驾驶） |

## 怎么跑

```powershell
# 编译（公共包在 zan-lang 仓库的 packages/ 下）
pwsh -File client/tools/build.ps1 -Compiler D:\project\zan-lang\build\zanc.exe `
    -Stdlib D:\project\zan-head\stdlib -PackageProject D:\project\zan-head

# 运行（build/arena/Arena.exe）
cd build/arena; .\Arena.exe
```

环境变量：

| 变量 | 作用 |
|------|------|
| `ARENA_SAVE=<dir>` | 存档目录（默认 `%LOCALAPPDATA%/Arena`） |
| `ARENA_SMOKE=1` | 无头冒烟：自动驾驶进对局，跑满 `ARENA_FRAMES` 帧后自行退出 |
| `ARENA_FRAMES=<n>` | 冒烟帧数（默认 90） |
| `ARENA_DEMO=1` | 演示模式：直接进对局并自动驾驶（截图 / 录屏用） |
| `ARENA_CAPTURE=<path.zpx>` | 渲染第 60 帧时把后端画布存成 ZPX（调试用，验收走窗口像素） |

## 怎么测

```powershell
pwsh -File client/tools/test.ps1 -Compiler D:\project\zan-lang\build\zanc.exe `
    -PackageProject D:\project\zan-head
```

三段全绿才算过：

1. `arena_test_OK` —— 玩法断言用例（`client/tests/arena_test.zan`，179 条
   断言）：波次数量递增与上限、三种敌人解锁波次、子弹命中扣血与死亡移除、
   玩家 HP 归零进结算、命中率统计、补给期恢复弹药/血量/耐力、圆与矩形碰撞
   判定、玩家穿不过墙与掩体、3 个随机种子的完整对局跑完且状态自洽。
2. `arena_SAVE_OK runs=1 -> runs=2` —— 存档写两遍读得到（第二遍是新进程）。
3. `arena_SMOKE_OK` —— 无头冒烟跑满帧退出。

截图验收（抓窗口像素，不是后端画布）：

```powershell
$env:ARENA_DEMO='1'
python D:\project\zan-lang\scripts\shot_window.py build\arena\Arena.exe `
    build\arena\shot.png 6 build\arena
```

## 代码结构

```
client/src/
  ArenaGame.zan     玩法核心：状态机（菜单/游戏中/结算）、波次推进、战斗结算、统计
  ArenaPlayer.zan   玩家：加速度与摩擦、瞄准、弹药、耐力冲刺
  ArenaEnemy.zan    三种敌人：属性、行为、受击
  ArenaBullet.zan   弹体（玩家与炮塔共用）
  ArenaPickup.zan   掉落物（弹药箱 / 医疗包）
  ArenaEffect.zan   爆炸特效
  ArenaWave.zan     波次规则：数量、解锁、兵种编排
  ArenaWorld.zan    地图与碰撞（960×600、墙体、5 处掩体）
  ArenaInput.zan    一帧输入结构（人玩与自动驾驶共用）
  ArenaSfx.zan      音效事件表（底层用公共包 SfxBank）
  ArenaView.zan     渲染层：贴图加载、战场、HUD、菜单、结算面板
  ArenaApp.zan      GuiHost 回调、输入采集、三个画面
  GameShell.zan     存档（最高波数/最高分/最高连杀/局数）+ 设置
  main.zan          GuiHost 入口
```

分层口径：**玩法逻辑不碰画布**（`ArenaGame` 及其依赖），渲染只在
`ArenaView`，输入只在 `ArenaApp`——所以玩法用例能脱离窗口直接跑完整局。

## 后续

1. 联机（`Game.Net.LockstepManager` 走确定性 tick + 客户端预测）。
2. 武器切换与更多兵种。
3. 背景音乐。
