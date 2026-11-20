"""把生图工具出的方形原图做成 240×240 聊天表情：清理透明通道、缩放、白描边、叠字。

用法：
    python3 build_stickers.py <原图目录> <输出目录> <文案.json> [--font 字体.ttf] [--gif]

原图目录里放 01.png、02.png……（透明底方图，512×512 最合适）。
文案.json 形如 {"01": "早", "05": "第一行\\n第二行"}，键对应文件名，\\n 换行。
默认字体是同仓库 fonts/ 下的站酷快乐体（SIL OFL 1.1，可免费商用）。
"""
import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
DEFAULT_FONT = HERE.parent / "fonts" / "ZCOOLKuaiLe-Regular.ttf"
S = 240
INK = (58, 30, 22, 255)      # 字色，取角色描边的同色系
EDGE = (255, 255, 255, 255)  # 白描边


def clean_alpha(im):
    """生图工具的透明底常有两个毛病：主体 alpha 不满 255（发虚），画布散着淡噪点。"""
    a = im.getchannel("A").point(lambda v: 0 if v < 32 else (255 if v >= 200 else v))
    im.putalpha(a)
    return im


def outline(im, px):
    """给透明底图加 px 宽白描边，聊天背景是深色时也不发糊。"""
    a = im.getchannel("A").point(lambda v: 255 if v > 40 else 0)
    grown = a.filter(ImageFilter.MaxFilter(px * 2 + 1))
    base = Image.new("RGBA", im.size, (255, 255, 255, 0))
    base.putalpha(grown)
    base.alpha_composite(im)
    return base


def fit_font(font_path, text, max_w, start):
    """从 start 字号往下试，直到一行放得下。"""
    size = start
    while size > 14:
        f = ImageFont.truetype(str(font_path), size)
        if f.getbbox(text)[2] <= max_w:
            return f
        size -= 1
    return f


def build(src, text, font_path, shift=12):
    im = clean_alpha(Image.open(src).convert("RGBA"))
    char = im.resize((S, S), Image.LANCZOS)
    # 人物下移，让下方的平切线贴着文字，不留白缝
    shifted = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    shifted.alpha_composite(char.crop((0, 0, S, S - shift)), (0, shift))
    canvas = outline(shifted, 2)
    lines = text.split("\n")
    longest = max(lines, key=len)
    f = fit_font(font_path, longest, S - 16, 40 if len(longest) <= 4 else 32)
    d = ImageDraw.Draw(canvas)
    lh = f.getbbox("国")[3] + 2
    y0 = S - 10 - lh * len(lines)  # 文字压在底部，多行整体上移
    for i, line in enumerate(lines):
        x, y = (S - f.getbbox(line)[2]) / 2, y0 + i * lh
        # 开源字体偏细：先画粗白边，再用同色 1px 描边把字身加粗
        d.text((x, y), line, font=f, fill=EDGE, stroke_width=5, stroke_fill=EDGE)
        d.text((x, y), line, font=f, fill=INK, stroke_width=1, stroke_fill=INK)
    return canvas


def save_gif(img, path):
    """静态 GIF，透明底，256 色。有些平台只收 GIF 时用。"""
    alpha = img.getchannel("A")
    p = img.convert("RGB").quantize(colors=255, method=Image.MEDIANCUT)
    p.paste(255, mask=alpha.point(lambda v: 255 if v < 128 else 0))
    p.save(path, transparency=255)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("texts")
    ap.add_argument("--font", default=str(DEFAULT_FONT))
    ap.add_argument("--gif", action="store_true", help="同时导出静态 GIF")
    a = ap.parse_args()
    src, out = Path(a.src), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    texts = json.loads(Path(a.texts).read_text(encoding="utf-8"))
    for n, text in sorted(texts.items()):
        img = build(src / f"{n}.png", text, a.font)
        img.save(out / f"{n}.png", optimize=True)
        if a.gif:
            save_gif(img, out / f"{n}.gif")
        print(n, (out / f"{n}.png").stat().st_size // 1024, "KB")


if __name__ == "__main__":
    main()
