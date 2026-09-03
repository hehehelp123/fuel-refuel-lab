# -*- coding: utf-8 -*-
"""Схема событийной метрики для слайда «Считаем события, а не точки»."""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Rectangle

OUT = "C:/Users/79101/Downloads/Лаба_заправки/slides_img/s_event_metric.png"
PURPLE = "#9307FE"
GREY = "#C4C4C4"
INK = "#1A1A1A"
GREEN = "#2E7D32"
RED = "#C62828"

plt.rcParams.update({"font.size": 10, "savefig.dpi": 200, "savefig.bbox": "tight"})

# колонки: (полоса, эталон, предсказание, подпись, цвет подписи)
COLS = [
    ((0.88, 2.90), (1.35, 2.45), (1.65, 2.70), "совпало\nTP", GREEN),
    ((3.35, 4.35), None, (3.55, 4.15), "лишнее\nFP", RED),
    ((5.15, 6.45), (5.35, 6.25), None, "пропущено\nFN", RED),
    ((7.55, 9.05), (7.75, 8.75), (7.70, 8.85), "совпало\nTP", GREEN),
]

Y_TRUE, Y_PRED, H = 2.10, 1.10, 0.50

fig, ax = plt.subplots(figsize=(6.2, 2.5))
ax.set_xlim(-0.6, 9.6)
ax.set_ylim(0.0, 3.35)
ax.axis("off")

for (bx0, bx1), truth, pred, caption, color in COLS:
    ax.add_patch(Rectangle((bx0, 0.95), bx1 - bx0, 1.75,
                           facecolor="#F2F2F2", lw=0, zorder=0))
    if truth:
        ax.add_patch(Rectangle((truth[0], Y_TRUE), truth[1] - truth[0], H,
                               facecolor=GREY, lw=0, zorder=2))
    if pred:
        ax.add_patch(Rectangle((pred[0], Y_PRED), pred[1] - pred[0], H,
                               facecolor=PURPLE, lw=0, zorder=2))
    ax.text((bx0 + bx1) / 2, 0.30, caption, ha="center", va="center",
            fontsize=10.5, color=color, linespacing=1.4)

# подписи рядов
ax.text(0.74, Y_TRUE + H / 2, "эталон", ha="right", va="center",
        fontsize=11, color="#666666")
ax.text(0.74, Y_PRED + H / 2, "модель", ha="right", va="center",
        fontsize=11, color="#666666")

# допуск: подсветка вокруг первого эталонного события
t0, t1 = COLS[0][1]
TOL = 0.42
ax.add_patch(Rectangle((t0 - TOL, Y_TRUE - 0.09), (t1 - t0) + 2 * TOL, H + 0.18,
                       facecolor=PURPLE, alpha=0.20, lw=0, zorder=1))
ax.text((t0 + t1) / 2, Y_TRUE + H + 0.30, "допуск ±5 минут",
        ha="center", fontsize=10.5, color=PURPLE)

# ось времени
ax.add_patch(FancyArrowPatch((0.88, 0.80), (9.35, 0.80), arrowstyle="-|>",
                             mutation_scale=9, lw=1.0, color=INK))
ax.text(9.45, 0.80, "время", ha="left", va="center", fontsize=10, color=INK)

plt.tight_layout()
os.makedirs(os.path.dirname(OUT), exist_ok=True)
fig.savefig(OUT)
plt.close(fig)
print("сохранено:", OUT)
