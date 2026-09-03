# -*- coding: utf-8 -*-
"""Пример заправки с выключенным двигателем и схема окна.

Схема событийной метрики — в fig_event_metric.py, график для вопроса
со звёздочкой — в analyze_off_task.py, остальное — в make_slide_figs.py.
"""
import os

import matplotlib
import matplotlib.dates as mdates
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyArrowPatch, Rectangle

RAW = "C:/Users/79101/Downloads/Лаба_заправки/data/fuel_raw.csv.gz"
OUT = "C:/Users/79101/Downloads/Лаба_заправки/slides_img"
os.makedirs(OUT, exist_ok=True)

PURPLE = "#9307FE"
INK = "#1A1A1A"
GREY = "#9A9A9A"

plt.rcParams.update({
    "font.size": 10,
    "axes.grid": True,
    "grid.alpha": 0.3,
    "legend.frameon": False,
    "savefig.dpi": 200,
    "savefig.bbox": "tight",
})


# ------------------------------------------- 1. заправка при заглушенном двигателе
def fig_ign_off():
    print("читаю сырые сообщения...")
    df = pd.read_csv(RAW, parse_dates=["ts"],
                     dtype={"vehicle": "category", "fuel_raw": "float32",
                            "fuel_l": "float32", "ign": "int8",
                            "speed": "float32", "marked": "int8"})
    print(f"  {len(df)} строк")

    best = None
    for veh, g in df.groupby("vehicle", observed=True):
        g = g.drop_duplicates("ts").reset_index(drop=True)
        idle = (g.fuel_raw.values <= 1.0)
        marked = g.marked.values == 1
        # непрерывные участки молчания датчика
        edges = np.diff(np.concatenate(([0], idle.view(np.int8), [0])))
        for a, b in zip(np.where(edges == 1)[0], np.where(edges == -1)[0] - 1):
            if not marked[a:b + 1].any():
                continue
            gap_min = (g.ts[b] - g.ts[a]).total_seconds() / 60
            if not 8 <= gap_min <= 45:
                continue
            before = g.fuel_l.values[max(0, a - 40):a]
            after = g.fuel_l.values[b + 1:b + 41]
            before = before[before > 1]
            after = after[after > 1]
            if len(before) < 15 or len(after) < 15:
                continue
            rise = np.median(after[:15]) - np.median(before[-15:])
            if rise < 25:
                continue
            score = min(rise, 60) + min(len(after), 40)
            if best is None or score > best[0]:
                best = (score, veh, a, b, g)

    if best is None:
        print("  подходящего события не нашлось")
        return
    _, veh, a, b, g = best

    lo = max(0, a - 45)
    hi = min(len(g) - 1, b + 45)
    w = g.iloc[lo:hi + 1]
    valid = w.fuel_l.values > 1

    fig, ax = plt.subplots(figsize=(6.0, 2.6))
    ax.plot(w.ts, np.where(valid, w.fuel_l, np.nan), lw=1.6, color=INK)
    ax.axvspan(g.ts[a], g.ts[b], color=PURPLE, alpha=0.16, lw=0,
               label="двигатель выключен, датчик молчит")

    lvl_before = np.median(g.fuel_l.values[max(0, a - 15):a])
    lvl_after = np.median(g.fuel_l.values[b + 1:b + 16])
    ax.annotate(f"{lvl_before:.0f} л", (g.ts[a], lvl_before),
                textcoords="offset points", xytext=(-6, 8), ha="right", fontsize=11)
    ax.annotate(f"{lvl_after:.0f} л", (g.ts[b], lvl_after),
                textcoords="offset points", xytext=(6, 4), fontsize=11)

    ax.set_ylabel("литры")
    ax.set_ylim(0, max(lvl_after * 1.35, 10))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    ax.legend(loc="upper left", fontsize=9)
    fig.savefig(os.path.join(OUT, "s_ign_off.png"))
    plt.close(fig)
    print(f"  s_ign_off.png: {veh}, {g.ts[a]:%d.%m.%Y}, "
          f"{lvl_before:.0f} -> {lvl_after:.0f} л, пропуск "
          f"{(g.ts[b]-g.ts[a]).total_seconds()/60:.0f} мин")


# ------------------------------------------------------------- 2. схема окна
def fig_window():
    fig, ax = plt.subplots(figsize=(6.0, 2.0))
    ax.set_xlim(-0.5, 7.2)
    ax.set_ylim(-1.15, 1.5)
    ax.axis("off")
    ax.grid(False)

    for i in range(7):
        center = (i == 3)
        ax.add_patch(Rectangle((i, 0), 0.86, 0.7, lw=1.2,
                               edgecolor=PURPLE if center else "#BBBBBB",
                               facecolor=PURPLE if center else "#FFFFFF"))
        ax.text(i + 0.43, 0.35, str(i + 1), ha="center", va="center", fontsize=11,
                color="white" if center else INK,
                fontweight="bold" if center else "normal")

    ax.annotate("", xy=(0, -0.18), xytext=(6.86, -0.18),
                arrowprops=dict(arrowstyle="<->", color=INK, lw=1.0))
    ax.text(3.43, -0.45, "окно: 7 интервалов = 35 минут", ha="center", fontsize=11)

    ax.add_patch(FancyArrowPatch((3.43, 1.28), (3.43, 0.78), arrowstyle="-|>",
                                 mutation_scale=11, color=PURPLE, lw=1.4))
    ax.text(3.43, 1.4, "класс окна = класс центрального интервала",
            ha="center", fontsize=11, color=PURPLE)
    ax.text(3.43, -0.95, "признаки каждого интервала: уровень и 4 разности",
            ha="center", fontsize=10, color="#666666")

    fig.savefig(os.path.join(OUT, "s_window.png"))
    plt.close(fig)
    print("  s_window.png")


fig_window()
fig_ign_off()
print("готово:", sorted(os.listdir(OUT)))
