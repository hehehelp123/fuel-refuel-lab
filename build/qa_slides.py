# -*- coding: utf-8 -*-
"""Проверка презентации: текст по слайдам, выход за границы, пропорции картинок."""
import glob
import os

from PIL import Image
from pptx import Presentation
from pptx.util import Emu

DECK = "C:/Users/79101/Downloads/Лаба_заправки/Лаба_заправки.pptx"
IMG = "C:/Users/79101/Downloads/Лаба_заправки/slides_img"

print("=== пропорции исходных PNG ===")
for p in sorted(glob.glob(os.path.join(IMG, "*.png"))):
    w, h = Image.open(p).size
    print(f"  {os.path.basename(p):18s} {w}x{h}  aspect {w / h:.3f}")

prs = Presentation(DECK)
SW, SH = prs.slide_width / 914400, prs.slide_height / 914400
print(f"\nхолст: {SW:.2f} x {SH:.2f} дюйма, слайдов: {len(prs.slides)}\n")

problems = []
for i, slide in enumerate(prs.slides, 1):
    texts = []
    for sh in slide.shapes:
        if sh.left is None:
            continue
        x, y = sh.left / 914400, sh.top / 914400
        w = (sh.width or 0) / 914400
        h = (sh.height or 0) / 914400

        if x < 0.25 or y < 0.2 or x + w > SW - 0.25 + 1e-6 or y + h > SH - 0.2 + 1e-6:
            problems.append(f"слайд {i}: {sh.shape_type} выходит за поля "
                            f"({x:.2f},{y:.2f}) {w:.2f}x{h:.2f}")

        if sh.shape_type == 13:                      # PICTURE
            iw, ih = sh.image.size
            src, dst = iw / ih, w / h
            if abs(src - dst) / src > 0.02:
                problems.append(f"слайд {i}: картинка искажена, "
                                f"исходная {src:.3f} против {dst:.3f}")

        if sh.has_text_frame and sh.text_frame.text.strip():
            texts.append((sh.text_frame.text.strip(), w, h, sh))

    print(f"--- слайд {i} " + "-" * 46)
    for t, w, h, sh in texts:
        first = t.splitlines()[0]
        print(f"  [{w:4.1f}x{h:4.1f}] {first[:78]}")

    # грубая оценка переполнения: сколько строк влезет против того, сколько нужно
    for t, w, h, sh in texts:
        size = None
        for para in sh.text_frame.paragraphs:
            for run in para.runs:
                if run.font.size:
                    size = run.font.size.pt
                    break
            if size:
                break
        if not size:
            size = 16.0          # размер по умолчанию из макета шаблона
        char_w = size * 0.5 / 72                      # средняя ширина знака, дюймы
        per_line = max(1, int(w / char_w))
        need = sum(max(1, -(-len(ln) // per_line)) for ln in t.splitlines())
        fits = max(1, int(h / (size * 1.25 / 72)))
        if need > fits:
            problems.append(f"слайд {i}: возможное переполнение "
                            f"({need} строк против {fits}) — «{t.splitlines()[0][:50]}»")

print("\n=== замечания ===")
if problems:
    for p in problems:
        print(" ", p)
else:
    print("  чисто")
