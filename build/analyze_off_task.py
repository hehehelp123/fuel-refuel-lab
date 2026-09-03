# -*- coding: utf-8 -*-
"""Насколько задача off-модели отделима одним вычитанием.

Для каждого провала в данных (двигатель заглушен) считаем уровень до и после
и проверяем, отличает ли простой порог на разнице экспертные заправки
от обычных стоянок.
"""
import io
import sqlite3

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

SRC = "C:/Users/79101/Downloads/Лаба_заправки/build/make_dataset.py"
DB = "C:/Users/79101/Documents/GitHub/FuelRemove/instance/app.db"

src = io.open(SRC, encoding="utf-8").read()
src = src[:src.index("sessions = pd.read_sql")]
ns = {}
exec(compile(src, "<make_dataset>", "exec"), ns)
collapse_zero_zones = ns["collapse_zero_zones"]
apply_labels = ns["apply_labels"]

con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
sessions = pd.read_sql("select id from upload_session order by id", con)

rows = []
for sid in sessions.id:
    q = """select message_time, sensor2_raw, sensor2_smoothed, ignition, speed,
                  original_label, label
           from track_point where session_id=? order by message_time"""
    pts = pd.read_sql(q, con, params=(sid,), parse_dates=["message_time"])
    if pts.empty:
        continue
    lbl = pts["original_label"].fillna(pts["label"]).fillna("").str.lower()
    df = pd.DataFrame({
        "ts": pts["message_time"],
        "fuel": pts["sensor2_smoothed"].fillna(0.0),
        "raw": pts["sensor2_raw"].fillna(pts["sensor2_smoothed"]).fillna(0.0),
        "ign": pts["ignition"].fillna(0.0),
        "speed": pts["speed"].fillna(0.0),
        "db_label": np.where(lbl.str.contains("fill|заправка"), "fill", "neutral"),
    })

    lab = apply_labels(collapse_zero_zones(df)).reset_index(drop=True)
    fuel = lab.fuel.values
    is_rep = lab.is_rep.values          # точка, в которую схлопнут провал
    final = lab.final_label.values

    for i in np.where(is_rep)[0]:
        if i == 0 or i == len(lab) - 1:
            continue
        rows.append({
            "sid": sid,
            "before": fuel[i - 1],
            "after": fuel[i + 1],
            "diff": fuel[i + 1] - fuel[i - 1],
            # событие класса 1 — это тройка вокруг провала
            "is_event": int(final[i] == 1),
        })

g = pd.DataFrame(rows)
print(f"всего провалов в данных: {len(g)}")
print(f"из них размечены как заправка (класс 1): {int(g.is_event.sum())}")
print()

pos = g[g.is_event == 1]["diff"]
neg = g[g.is_event == 0]["diff"]
print("разница «уровень после минус уровень до», литров")
print(f"  заправки : медиана {pos.median():7.2f}, "
      f"5-й перцентиль {pos.quantile(.05):7.2f}, минимум {pos.min():7.2f}")
print(f"  не заправки: медиана {neg.median():7.2f}, "
      f"95-й перцентиль {neg.quantile(.95):7.2f}, максимум {neg.max():7.2f}")
print()

print("отделимость простым порогом на этой разнице:")
best = None
for thr in [0.5, 1, 2, 3, 5, 8, 10, 15, 20]:
    pred = (g["diff"] > thr).astype(int)
    tp = int(((pred == 1) & (g.is_event == 1)).sum())
    fp = int(((pred == 1) & (g.is_event == 0)).sum())
    fn = int(((pred == 0) & (g.is_event == 1)).sum())
    p = tp / (tp + fp) if tp + fp else 0
    r = tp / (tp + fn) if tp + fn else 0
    f1 = 2 * p * r / (p + r) if p + r else 0
    print(f"  порог {thr:5.1f} л: precision {p:.3f}  recall {r:.3f}  F1 {f1:.3f}")
    if best is None or f1 > best[1]:
        best = (thr, f1)
print()
print(f"лучший порог: {best[0]} л, F1 = {best[1]:.3f}")
print()
print("Если одно вычитание даёт F1 около единицы, то 100% у сети означают,")
print("что она воспроизвела это вычитание, а не научилась чему-то большему.")

# ---------------------------------------------- картинка для вопроса со звёздочкой
ACCENT, GREY = "#9307FE", "#9A9A9A"
plt.rcParams.update({"font.size": 10, "axes.grid": True, "grid.alpha": 0.3,
                     "legend.frameon": False, "savefig.dpi": 200,
                     "savefig.bbox": "tight"})
OUT = "C:/Users/79101/Downloads/Лаба_заправки/slides_img/s_leak.png"

bins = np.linspace(-5, 60, 66)
fig, ax = plt.subplots(figsize=(5.6, 2.6))
ax.hist(neg.clip(-5, 60), bins=bins, color=GREY, label="обычная стоянка")
ax.hist(pos.clip(-5, 60), bins=bins, color=ACCENT, alpha=0.85, label="заправка")
ax.axvline(best[0], color="#1A1A1A", ls="--", lw=1.2)
ax.annotate(f"порог {best[0]:.0f} л: F1 = {best[1]:.3f}", (best[0], 120),
            xytext=(8, 0), textcoords="offset points", fontsize=10)
ax.set_yscale("log")
ax.set_xlabel("уровень после стоянки минус уровень до, литров")
ax.set_ylabel("число стоянок")
ax.legend(fontsize=9)
plt.tight_layout()
fig.savefig(OUT)
plt.close(fig)
print("картинка сохранена:", OUT)
