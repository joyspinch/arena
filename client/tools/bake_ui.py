#!/usr/bin/env python3
"""bake_ui.py — 生成 UI 底板（按钮板 / 面板 / 落地投影）。

为什么要有底板：画布上的按钮与面板原先是"圆角矩形 + 纯色 + 系统风文字"，
没有美术底板。这里离线画出**九宫格可拉伸**的工业风底板（切角钢板 +
斜面高光 + 描边），运行时用 CDraw 裁源矩形拼 9 块（引擎没有 border-image，
九宫格得自己切）。

产出（都在 client/assets/ 下）：
  ui_plate.png / ui_plate_hi.png / ui_plate_down.png      —— 次要按钮三态
  ui_plate_primary*.png                                   —— 主按钮三态
  ui_panel.png                                            —— 面板底板
  shadow.png                                              —— 椭圆落地投影

板子尺寸 48×36、面板 64×64，切角都是 12px / 16px 以内，九宫格的切角
尺寸取板子边长的 1/4（见 client/src/ArenaView.zan 的 DrawNineSlice）。

用法：
    python client/tools/bake_ui.py [--assets <assets 目录>]
"""

import argparse
import os

import numpy as np
from PIL import Image

# 板子切角（九宫格的 border = 边长 // 4）。
PLATE_W, PLATE_H = 48, 36
PANEL_W, PANEL_H = 64, 64
CHAMFER = 6          # 板子切角（45° 斜切）
PANEL_CHAMFER = 10

# 三态配色：常态 / 悬停 / 按下。键名对应产出文件名后缀。
PLATES = {
    "ui_plate": dict(
        body=(30, 40, 51), top=(48, 62, 79), bottom=(17, 23, 30),
        edge=(62, 80, 99)),
    "ui_plate_hi": dict(
        body=(41, 54, 68), top=(64, 84, 106), bottom=(24, 32, 41),
        edge=(232, 134, 43)),
    "ui_plate_down": dict(
        body=(20, 27, 35), top=(13, 18, 24), bottom=(52, 68, 85),
        edge=(168, 95, 26)),
    "ui_plate_primary": dict(
        body=(200, 116, 30), top=(232, 145, 48), bottom=(142, 84, 20),
        edge=(240, 160, 80)),
    "ui_plate_primary_hi": dict(
        body=(224, 134, 42), top=(248, 170, 70), bottom=(160, 94, 24),
        edge=(255, 200, 140)),
    "ui_plate_primary_down": dict(
        body=(142, 84, 20), top=(112, 66, 16), bottom=(210, 126, 36),
        edge=(192, 106, 32)),
}


def chamfer_mask(w, h, cut):
    """切角八边形掩码（alpha 0/1）。"""
    m = Image.new("L", (w, h), 255)
    px = m.load()
    for y in range(h):
        for x in range(w):
            # 四个 45° 斜角：距角越近切得越多。
            dx = min(x, w - 1 - x)
            dy = min(y, h - 1 - y)
            if dx < cut and dy < cut and (cut - dx) + (cut - dy) > cut:
                px[x, y] = 0
    return m


def bevel_mask(w, h, cut, width):
    """上/左沿的亮边与下/右沿的暗边（内缩 width 像素）。"""
    top = Image.new("L", (w, h), 0)
    bot = Image.new("L", (w, h), 0)
    tp = top.load()
    bp = bot.load()
    for y in range(h):
        for x in range(w):
            dist_left = x
            dist_right = w - 1 - x
            dist_top = y
            dist_bottom = h - 1 - y
            if min(dist_top, dist_left) < width:
                tp[x, y] = 255
            if min(dist_bottom, dist_right) < width:
                bp[x, y] = 255
    return top, bot


def draw_plate(w, h, cut, spec, edge_width=2):
    """切角钢板：底色 + 上/左亮边 + 下/右暗边 + 描边。"""
    body, top, bottom, edge = (spec["body"], spec["top"], spec["bottom"],
                               spec["edge"])
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px = img.load()
    mask = chamfer_mask(w, h, cut)
    mp = mask.load()
    hi, lo = bevel_mask(w, h, cut, 3)
    hp = hi.load()
    lop = lo.load()
    for y in range(h):
        for x in range(w):
            if mp[x, y] == 0:
                continue
            if hp[x, y]:
                r, g, b = top
            elif lop[x, y]:
                r, g, b = bottom
            else:
                r, g, b = body
            # 描边：贴着切角轮廓的一圈。
            if not _inside(mask, x, y):
                r, g, b = edge
            px[x, y] = (r, g, b, 255)
    return img


def _inside(mask, x, y):
    """(x,y) 是否在切角轮廓内侧至少 1 像素。

    越界也算"在外面"——否则贴图最外圈永远描不上边。
    """
    w, h = mask.size
    for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
        if nx < 0 or ny < 0 or nx >= w or ny >= h:
            return False
        if mask.getpixel((nx, ny)) == 0:
            return False
    return True


def draw_panel(w, h, cut):
    """面板底板：深钢蓝底 + 橙色描边 + 四角托架（角托架在九宫格的角块里）。"""
    body = (24, 32, 42)
    edge = (232, 134, 43)
    inner = (32, 43, 56)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px = img.load()
    mask = chamfer_mask(w, h, cut)
    mp = mask.load()
    for y in range(h):
        for x in range(w):
            if mp[x, y] == 0:
                continue
            border = not _inside(mask, x, y)
            # 四角托架：角上 14px 见方的 L 形。
            corner_x = min(x, w - 1 - x)
            corner_y = min(y, h - 1 - y)
            bracket = corner_x < 14 and corner_y < 14 and (
                corner_x < 3 or corner_y < 3
                or (corner_x < 14 and abs(corner_x - corner_y) < 3
                    and corner_x > 3))
            if border or bracket:
                r, g, b = edge
            elif y < 3:
                r, g, b = inner
            else:
                r, g, b = body
            px[x, y] = (r, g, b, 255)
    return img


def draw_shadow(w, h):
    """椭圆落地投影：中心黑、边缘平滑衰减到透明。"""
    yy, xx = np.mgrid[0:h, 0:w]
    cx, cy = (w - 1) / 2.0, (h - 1) / 2.0
    rx, ry = w / 2.0 - 1.0, h / 2.0 - 1.0
    d = np.sqrt(((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2)
    t = np.clip((1.0 - d) / 0.45, 0.0, 1.0)
    a = (t * t * (3.0 - 2.0 * t) * 255.0).astype(np.uint8)
    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    rgba[:, :, 3] = a
    return Image.fromarray(rgba, "RGBA")


def main():
    ap = argparse.ArgumentParser()
    root = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    ap.add_argument("--assets", default=os.path.join(root, "client", "assets"))
    args = ap.parse_args()
    os.makedirs(args.assets, exist_ok=True)

    for name, spec in PLATES.items():
        img = draw_plate(PLATE_W, PLATE_H, CHAMFER, spec)
        path = os.path.join(args.assets, name + ".png")
        img.save(path, optimize=True)
        print("%-22s %dx%d  %d 字节" % (name + ".png", PLATE_W, PLATE_H,
                                        os.path.getsize(path)))

    panel = draw_panel(PANEL_W, PANEL_H, PANEL_CHAMFER)
    path = os.path.join(args.assets, "ui_panel.png")
    panel.save(path, optimize=True)
    print("%-22s %dx%d  %d 字节" % ("ui_panel.png", PANEL_W, PANEL_H,
                                    os.path.getsize(path)))

    shadow = draw_shadow(96, 48)
    path = os.path.join(args.assets, "shadow.png")
    shadow.save(path, optimize=True)
    print("%-22s %dx%d  %d 字节" % ("shadow.png", 96, 48,
                                    os.path.getsize(path)))


if __name__ == "__main__":
    main()
