# -*- coding: utf-8 -*-
"""Прогоняет ячейки ноутбука и сохраняет картинки для презентации."""
import json
import os

import matplotlib
import matplotlib.dates
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

NB = "C:/Users/79101/Downloads/Лаба_заправки/Fuel_Refuel_Detection_Lab.ipynb"
CSV = "C:/Users/79101/Downloads/Лаба_заправки/data/fuel_5min.csv"
OUT = "C:/Users/79101/Downloads/Лаба_заправки/slides_img"
os.makedirs(OUT, exist_ok=True)

ACCENT = "#9307FE"   # фирменный фиолетовый ИТМО
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

with open(NB, encoding="utf-8") as f:
    nb = json.load(f)

env = {"__name__": "__main__"}
for cell in nb["cells"]:
    if cell["cell_type"] != "code":
        continue
    src = "".join(cell["source"])
    if "files.upload" in src:
        src = src.replace('LOCAL = "fuel_5min.csv"', f'LOCAL = r"{CSV}"')
        src = src.replace("if not os.path.exists(LOCAL):", "if False:")
    exec(compile(src, "<cell>", "exec"), env)
    plt.close("all")

y_test = env["y_test"]
y_pred = env["y_pred"]
df = env["df"]
lstm_f1 = env["lstm_events"]["f1"]
best_thr_f1 = env["best_thr_f1"]

# ------------------------------------------------------------- 1. дисбаланс
counts = df["label"].value_counts().sort_index()
fig, ax = plt.subplots(figsize=(5.2, 2.9))
bars = ax.bar(["0 — ничего", "1 — на ходу", "2 — на стоянке"], counts.values,
              color=[GREY, ACCENT, "#6E6E6E"])
ax.set_ylabel("бинов по 5 минут")
ax.set_yscale("log")
for b, v in zip(bars, counts.values):
    ax.text(b.get_x() + b.get_width() / 2, v * 1.15, f"{v:,}".replace(",", " "),
            ha="center", fontsize=10)
plt.tight_layout()
fig.savefig(os.path.join(OUT, "s_balance.png"))
plt.close(fig)

# ------------------------------------------------- 2. confusion matrix лабы
from sklearn.metrics import confusion_matrix

cm = confusion_matrix(y_test, y_pred, labels=[0, 1, 2])
fig, ax = plt.subplots(figsize=(3.6, 3.2))
ax.imshow(cm / cm.sum(axis=1, keepdims=True).clip(min=1), cmap="Greys", vmin=0, vmax=1.3)
for i in range(3):
    for j in range(3):
        share = cm[i, j] / max(cm[i].sum(), 1)
        ax.text(j, i, f"{cm[i, j]}", ha="center", va="center", fontsize=12,
                color="white" if share > 0.55 else "black")
ax.set_xticks(range(3), ["0", "1", "2"])
ax.set_yticks(range(3), ["0", "1", "2"])
ax.set_xlabel("предсказано")
ax.set_ylabel("на самом деле")
ax.grid(False)
plt.tight_layout()
fig.savefig(os.path.join(OUT, "s_confusion.png"))
plt.close(fig)

# ------------------------------------------------------- 3. LSTM против порога
fig, ax = plt.subplots(figsize=(4.4, 2.9))
bars = ax.bar(["пороговое правило", "LSTM"], [best_thr_f1, lstm_f1],
              color=[GREY, ACCENT], width=0.55)
for b, v in zip(bars, [best_thr_f1, lstm_f1]):
    ax.text(b.get_x() + b.get_width() / 2, v + 0.02, f"{v:.3f}", ha="center", fontsize=12)
ax.set_ylim(0, 1.05)
ax.set_ylabel("событийный F1")
plt.tight_layout()
fig.savefig(os.path.join(OUT, "s_compare.png"))
plt.close(fig)

# --------------------------------------------- 4. пример заправки на ходу
top = df[df.label == 1].groupby("vehicle").size().sort_values(ascending=False).index[0]
g = df[df.vehicle == top].reset_index(drop=True)
ev = env["events_of"](g)
s, e = ev[len(ev) // 2]
lo, hi = max(0, s - 12), min(len(g) - 1, e + 12)
w = g.iloc[lo:hi + 1]

fig, ax = plt.subplots(figsize=(6.0, 2.6))
ax.plot(w.ts, w.fuel, marker="o", ms=3.5, lw=1.4, color=INK)
ax.axvspan(g.ts[s], g.ts[e], color=ACCENT, alpha=0.16, label="размеченная заправка")
ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%H:%M"))
ax.set_ylabel("литры")
ax.set_xlabel(f"{top}, {g.ts[s]:%d.%m.%Y}")
ax.legend(fontsize=9)
plt.tight_layout()
fig.savefig(os.path.join(OUT, "s_event.png"))
plt.close(fig)

print("картинки:", os.listdir(OUT))
print(f"событийный F1: LSTM {lstm_f1:.3f}, порог {best_thr_f1:.3f}")
print("confusion matrix:\n", cm)
