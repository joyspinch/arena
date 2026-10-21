# 裂谷竞技 —— 2D 俯视多人竞技（射击）

> 本文件是 arena 项目的落地说明。**素材清单见 `client/ASSETS.md`**，全局规格见工作区根的 `ASSET-PIPELINE.md`。

## 参考源与授权边界

- **参考**：Teeworlds（`datasrc/` 素材 CC-BY-SA 3.0，字体除外）
- **抄什么**：抄俯视视角、teams 阵营机制、武器切换、死亡重生点、tie 判定。角色与 UI 自研。

**红线与差异**：

- Teeworlds 素材在 `datasrc/`，需 `scripts/build.py` 生成 `data/`；**音乐只有 1 首**，BGM 全部自研。
- Teeworlds 联机是自研 UDP 协议；本项目先做单机，联网属后续阶段（不在 P0）。
- 不移植 `maps/` 与 `languages/`（均为 submodule）。

## 渲染路线

2D 贴图批 + 视角跟随相机。角色 5 向 + 镜像；子弹、枪口焰、爆炸为独立小图。

## 目录

    arena/
      client/       src/ 源码、assets/ 素材、data/ 数据、skins/ 皮肤、tools/ 脚本、tests/ 用例
      build/        编译产物（不入库）

所有命令都在**项目根**下执行（路径相对项目根）。

## 编译

```powershell
$env:ZAN_HOME = 'D:/project/zan-lang'   # 编译器与 stdlib 同源；公共包在它的 packages/ 下
pwsh -File client/tools/build.ps1
```

ZAN_HOME 指向 zan-lang 仓库时用它的 `build/zanc.exe` 与 `stdlib/`；不设则用 PATH 上的 `zanc`。
编译时加 `--package-project $env:ZAN_HOME` 可直接吃仓库里的 `packages/`。

## 测试

```powershell
pwsh -File client/tools/test.ps1     # 无头冒烟：跑满 90 帧后自行退出
```

工作区批量冒烟：`pwsh -File tools/smoke-all.ps1`（一次跑完 10 个新项目）。

## 当前状态

骨架可编译可运行（90 帧无头冒烟通过）：俯视竞技场、瞄准射击、阵营计分。

## 后续（按优先级）

1. 接入真实位图 sprite 与音效（素材见 `client/ASSETS.md`）。
2. 补玩法深度：参照源的关卡/数值/AI 三个维度逐项对齐。
3. 需要时再评估联网（`legend` 有服务端可参考）。