#!/usr/bin/env python3
"""bake_facing.py — 把主体位图离线烘成"方向精灵表"。

为什么必须离线烘：引擎运行时转不了图——`Canvas.BlitImage` 只有源矩形
(sx,sy,sw,sh)，没有旋转、没有水平翻转，`Gui.SpriteBatch` 的每精灵也只
有 dx/dy/dw/dh/sx/sy/sw/sh/tint。所以"运行时把角色转个方向"做不到，朝向
只能在素材阶段烘好，运行时按角度取帧。

做法（照 racekart 的 process_assets.py 那一套）：
  1. AI 原图（纯黑底）→ 洪泛抠 alpha → 裁到主体区域；
  2. 主体绕**旋转轴**摆进一张正方画布（画布边长 = 2×主体最大半径 + 余量，
     主体因此落在内切圆里，旋转不裁角）；
  3. 画布缩到 cell×2，绕心旋成 N 个角度（正角 = 顺时针，与"帧 0 正面朝上、
     之后每帧顺时针 step 度"一致），拼成一条横条精灵表（帧宽 = 帧高 = cell）；
  4. 旋转用"预乘 alpha → 旋转 → 反预乘"，半透明边缘的 RGB 不会被插值到黑
     （直接旋转 RGBA 会带出黑边）。

角度 → 帧号的映射是纯函数，跑在运行时（client/src/ArenaFacing.zan）：
帧 0 = 正面朝上，帧 i = 顺时针 i×(360/frames) 度。映射规则与帧数写进
client/ASSETS.md，用例（client/tests/arena_test.zan）钉住不回归。

用法：
    python client/tools/bake_facing.py [--raw <原图目录>] [--assets <assets 目录>]
                                      [--preview <预览输出目录>]
"""

import argparse
import math
import os
from collections import deque

import numpy as np
from PIL import Image

# 主体配置表。
#
# crop   —— 从原图里裁下的主体区域（原图像素，左上右下）。
# pivot  —— 旋转轴在原图里的位置：必须与实体在场景里的位置重合，
#           否则转起来会绕着别的点甩。玩家=头盔中心，炮塔=底座圆心，
#           冲锋兵=机腹发光眼，重装兵=机身核心。
# pre    —— 烘焙前的预旋转（度，正角 = 顺时针）。冲锋兵原图的机头朝下，
#           预转 180° 让"帧 0 = 正面朝上"成立。
# frames —— 精灵表帧数。
# cell   —— 每帧在精灵表里的边长（像素）= 运行时显示尺寸的 2 倍。
# display—— 运行时显示边长（逻辑像素）。
ENTITIES = [
    dict(name="player", raw="player",
         crop=(324, 60, 700, 470), pivot=(505, 395),
         pre=0, frames=16, cell=112, display=56),
    dict(name="chaser", raw="chaser",
         crop=(142, 80, 882, 942), pivot=(510, 505),
         pre=180, frames=8, cell=76, display=38),
    dict(name="turret", raw="turret",
         crop=(225, 200, 798, 1011), pivot=(510, 690),
         pre=0, frames=8, cell=112, display=56),
    dict(name="brute", raw="brute",
         crop=(64, 28, 960, 993), pivot=(510, 510),
         pre=0, frames=8, cell=144, display=72),
]


# ---------------------------------------------------------------- 抠图 ----

def corner_color(img):
    w, h = img.size
    samples = [img.getpixel((0, 0)), img.getpixel((w - 1, 0)),
               img.getpixel((0, h - 1)), img.getpixel((w - 1, h - 1))]
    counts = {}
    for c in samples:
        counts[c] = counts.get(c, 0) + 1
    return max(counts.items(), key=lambda kv: kv[1])[0]


def near(a, b, tol=42):
    return (abs(a[0] - b[0]) <= tol and abs(a[1] - b[1]) <= tol
            and abs(a[2] - b[2]) <= tol)


def cutout(img, tol=42):
    """从四边洪泛抠掉与底色相近的像素（纯黑底适用），返回 RGBA。"""
    img = img.convert("RGBA")
    w, h = img.size
    px = img.load()
    bg = corner_color(img)
    seen = bytearray(w * h)
    q = deque()
    for x in range(w):
        for y in (0, h - 1):
            if not seen[y * w + x] and near(px[x, y][:3], bg, tol):
                seen[y * w + x] = 1
                q.append((x, y))
    for y in range(h):
        for x in (0, w - 1):
            if not seen[y * w + x] and near(px[x, y][:3], bg, tol):
                seen[y * w + x] = 1
                q.append((x, y))
    while q:
        x, y = q.popleft()
        px[x, y] = (bg[0], bg[1], bg[2], 0)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if nx < 0 or ny < 0 or nx >= w or ny >= h:
                continue
            if seen[ny * w + nx]:
                continue
            if near(px[nx, ny][:3], bg, tol):
                seen[ny * w + nx] = 1
                q.append((nx, ny))
    # 主体身上的零散同底色像素（空洞）也清掉。
    for y in range(h):
        for x in range(w):
            if px[x, y][3] != 0 and near(px[x, y][:3], bg, tol):
                px[x, y] = (px[x, y][0], px[x, y][1], px[x, y][2], 0)
    return img


# ---------------------------------------------------------------- 旋转 ----

def rotate_clean(img, deg):
    """绕图心旋转 deg 度（PIL 正角 = 逆时针），消除黑边。

    做法：RGB 预乘 alpha → 旋转 → 反预乘。直接旋转 RGBA 时，BICUBIC 会把
    透明像素的黑色 RGB 插值进边缘，半透明边缘因此发黑（"黑边"）。
    """
    alpha = np.asarray(img.split()[3], dtype=np.float32) / 255.0
    rgb = np.asarray(img.convert("RGB"), dtype=np.float32)
    pre = rgb * alpha[:, :, None]
    pre_img = Image.fromarray(np.clip(pre, 0, 255).astype(np.uint8), "RGB")
    alpha_img = img.split()[3]

    rot_pre = np.asarray(pre_img.rotate(deg, resample=Image.BICUBIC),
                         dtype=np.float32)
    rot_alpha = np.asarray(alpha_img.rotate(deg, resample=Image.BICUBIC),
                           dtype=np.float32) / 255.0

    safe = np.maximum(rot_alpha, 1e-3)[:, :, None]
    straight = np.clip(rot_pre / safe, 0, 255)
    out = Image.fromarray(straight.astype(np.uint8), "RGB").convert("RGBA")
    out.putalpha(Image.fromarray(
        (np.clip(rot_alpha, 0.0, 1.0) * 255.0).astype(np.uint8), "L"))
    return out


def max_radius(img, pivot):
    """主体到旋转轴的最大距离（像素）——决定画布边长。"""
    alpha = img.split()[3]
    px = alpha.load()
    w, h = img.size
    r = 0.0
    for y in range(h):
        for x in range(w):
            if px[x, y] > 8:
                d = math.hypot(x - pivot[0], y - pivot[1])
                if d > r:
                    r = d
    return r


def square_canvas(img, pivot, margin=2):
    """把主体摆进正方画布，旋转轴落在画布正中。

    边长 = 2×最大半径 + 余量，主体因此整个落在内切圆里——任意角度旋转
    都不会裁到角。
    """
    r = max_radius(img, pivot)
    # 边长留 4% 余量：主体半径正好等于半径时，主体会贴到画布边缘，
    # 旋转后看起来像"被裁掉一截"。
    side = int(math.ceil(2.0 * r * 1.04)) + margin * 2
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    ox = int(round(side / 2.0 - pivot[0]))
    oy = int(round(side / 2.0 - pivot[1]))
    canvas.paste(img, (ox, oy), img)
    return canvas


# ---------------------------------------------------------------- 烘焙 ----

def bake_entity(cfg, raw_dir, assets_dir, preview_dir=None):
    name = cfg["name"]
    src_path = os.path.join(raw_dir, cfg["raw"] + ".png")
    if not os.path.exists(src_path):
        raise SystemExit("缺少原图：%s" % src_path)

    full = cutout(Image.open(src_path))
    crop = cfg["crop"]
    body = full.crop(crop)
    pivot = (cfg["pivot"][0] - crop[0], cfg["pivot"][1] - crop[1])
    if pivot[0] < 0 or pivot[1] < 0 or pivot[0] >= body.width or pivot[1] >= body.height:
        raise SystemExit("%s 的旋转轴不在裁剪区内：%s vs %s" % (name, pivot, body.size))

    canvas = square_canvas(body, pivot)
    cell = cfg["cell"]
    frames = cfg["frames"]
    pre = cfg["pre"]
    step = 360.0 / frames

    # 画布先缩到 cell×2 再旋转：旋转在高分辨率上做，缩图只做一次。
    work = canvas.resize((cell * 2, cell * 2), Image.LANCZOS)
    strip = Image.new("RGBA", (cell * frames, cell), (0, 0, 0, 0))
    for i in range(frames):
        # 帧 i = 源图顺时针转 i×step 度（PIL 逆时针为正，取负）。
        deg = pre - i * step
        frame = rotate_clean(work, deg).resize((cell, cell), Image.LANCZOS)
        strip.paste(frame, (i * cell, 0), frame)
        if preview_dir:
            frame.save(os.path.join(preview_dir, "%s_%02d.png" % (name, i)))

    out_path = os.path.join(assets_dir, name + "_sheet.png")
    strip.save(out_path, optimize=True)
    print("%-10s %2d 帧 cell=%dx%d 显示=%dx%d  -> %s (%d 字节)"
          % (name, frames, cell, cell, cfg["display"], cfg["display"],
             os.path.basename(out_path), os.path.getsize(out_path)))
    return out_path


def main():
    ap = argparse.ArgumentParser()
    root = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    ap.add_argument("--raw", default=os.path.join(root, "_scratch", "raw"))
    ap.add_argument("--assets", default=os.path.join(root, "client", "assets"))
    ap.add_argument("--preview", default="")
    args = ap.parse_args()

    os.makedirs(args.assets, exist_ok=True)
    if args.preview:
        os.makedirs(args.preview, exist_ok=True)

    for cfg in ENTITIES:
        bake_entity(cfg, args.raw, args.assets, args.preview or None)

    total = 0
    for f in sorted(os.listdir(args.assets)):
        if f.endswith("_sheet.png"):
            total += os.path.getsize(os.path.join(args.assets, f))
    print("精灵表合计: %.1f KB" % (total / 1024.0))


if __name__ == "__main__":
    main()
