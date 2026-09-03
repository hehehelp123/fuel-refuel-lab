# -*- coding: utf-8 -*-
"""Сколько экспертных отметок доходит до обучения ветки «двигатель выключен»."""
import io
import sqlite3

import numpy as np
import pandas as pd

SRC = "C:/Users/79101/Downloads/Лаба_заправки/build/make_dataset.py"
DB = "C:/Users/79101/Documents/GitHub/FuelRemove/instance/app.db"

# берём из make_dataset.py только определения функций
src = io.open(SRC, encoding="utf-8").read()
src = src[:src.index("sessions = pd.read_sql")]
ns = {}
exec(compile(src, "<make_dataset>", "exec"), ns)
collapse_zero_zones = ns["collapse_zero_zones"]
apply_labels = ns["apply_labels"]

con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
sessions = pd.read_sql("select id, filename from upload_session order by id", con)

tot_expert = tot_c1 = tot_c2 = 0
tot_pts_c1 = tot_pts_c2 = 0

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

    # сколько отдельных участков отметил эксперт (по сырым сообщениям)
    marked = (df.db_label == "fill").values
    edges = np.diff(np.concatenate(([0], marked.astype(np.int8), [0])))
    n_expert = int((edges == 1).sum())

    labeled = apply_labels(collapse_zero_zones(df))
    blocks = labeled[labeled.final_label > 0].groupby("block")
    c1 = sum(1 for _, g in blocks if g.final_label.iloc[0] == 1)
    c2 = sum(1 for _, g in blocks if g.final_label.iloc[0] == 2)
    pts1 = int((labeled.final_label == 1).sum())
    pts2 = int((labeled.final_label == 2).sum())

    tot_expert += n_expert
    tot_c1 += c1
    tot_c2 += c2
    tot_pts_c1 += pts1
    tot_pts_c2 += pts2

print(f"участков, отмеченных экспертом:          {tot_expert}")
print(f"из них стали классом 1 (три точки с нулём): {tot_c1}")
print(f"из них стали классом 2 (всё остальное):     {tot_c2}")
print()
print(f"точек в классе 1: {tot_pts_c1}   точек в классе 2: {tot_pts_c2}")
print()
print("В обучении модели «двигатель выключен» класс 2 полностью выбрасывается")
print("(app/ml/engine.py: valid_idx = np.where(seq_y != 2) при model_type='off'),")
print(f"то есть до обучения доходит {tot_c1} событий из {tot_c1 + tot_c2},")
print(f"а именно те, что уже имеют нужную форму.")
