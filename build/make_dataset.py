# -*- coding: utf-8 -*-
"""Готовит учебный датасет по заправкам из instance/app.db проекта FuelRemove.

Повторяет офлайн препроцессинг EventExtractor (ветка ignition-on) и выгружает:
  data/fuel_5min.csv     — 5-минутные бины с метками, основной файл лабы
  data/fuel_raw.csv.gz   — сырые сообщения (для продвинутого задания)
Идентификаторы ТС анонимизируются (V01..V50), координаты не выгружаются.
"""
import os
import sqlite3

import numpy as np
import pandas as pd

DB = "C:/Users/79101/Documents/GitHub/FuelRemove/instance/app.db"
OUT = "C:/Users/79101/Downloads/Лаба_заправки/data"
SEQ_LEN = 7          # длина окна ign-on модели
TEST_RATIO = 0.2

os.makedirs(OUT, exist_ok=True)
con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)


# --------------------------------------------------------------------------
# препроцессинг, перенесённый из app/ml/event_extractor.py
# --------------------------------------------------------------------------
def collapse_zero_zones(df):
    """Схлопывает участки, где датчик молчит (raw <= 1), в одну точку."""
    time_arr = df['ts'].astype('int64').values // 10 ** 9
    raw_arr = df['raw'].values
    is_zero = raw_arr <= 1.0

    forward = np.zeros(len(df), dtype=bool)
    last_bad = -99999999999
    for i in range(len(df)):
        if is_zero[i]:
            last_bad = time_arr[i]
            forward[i] = True
        elif time_arr[i] - last_bad <= 10:
            forward[i] = True

    backward = np.zeros(len(df), dtype=bool)
    last_bad = 99999999999
    for i in range(len(df) - 1, -1, -1):
        if is_zero[i]:
            last_bad = time_arr[i]
            backward[i] = True
        elif last_bad - time_arr[i] <= 10:
            backward[i] = True

    df = df.copy()
    df['zero_zone'] = forward | backward
    df['block_id'] = (df['zero_zone'] != df['zero_zone'].shift()).cumsum()

    rows = []
    for _, group in df.groupby('block_id'):
        if group['zero_zone'].iloc[0]:
            has_fill = (group['db_label'] == 'fill').any()
            rep = group.iloc[len(group) // 2].copy()
            rep['fuel'] = 0.0
            rep['raw'] = 0.0
            rep['db_label'] = 'fill' if has_fill else 'neutral'
            rep['is_rep'] = True
            rows.append(rep.to_dict())
        else:
            g = group.copy()
            g['is_rep'] = False
            rows.extend(g.to_dict('records'))
    return pd.DataFrame(rows).reset_index(drop=True)


def apply_labels(df):
    """Из грубых меток оператора делает классы 1 (чистое событие) и 2 (остальное)."""
    df = df.copy()
    df['base_label'] = 0
    n = len(df)
    for i in range(n):
        if 'fill' in str(df.at[i, 'db_label']).lower():
            df.at[i, 'base_label'] = 1

    for i in range(n):
        if df.at[i, 'is_rep'] and df.at[i, 'base_label'] == 1:
            if i > 0:
                df.at[i - 1, 'base_label'] = 1
            if i < n - 1:
                df.at[i + 1, 'base_label'] = 1

    df['block'] = (df['base_label'] != df['base_label'].shift()).cumsum()

    def is_stable(vals):
        if len(vals) <= 1:
            return True
        m = np.mean(vals)
        if m == 0:
            return True
        return (np.max(vals) - np.min(vals)) <= 0.1 * m

    for _, group in df[df['base_label'] == 1].groupby('block'):
        if len(group) < 10:
            zeros = group[group['fuel'] == 0.0]
            if len(zeros) == 1:
                z = zeros.index[0]
                before = df.loc[group.index[group.index < z], 'fuel'].values
                after = df.loc[group.index[group.index > z], 'fuel'].values
                if is_stable(before) and is_stable(after):
                    keep = [z - 1, z, z + 1]
                    drop = [i for i in group.index if i not in keep]
                    if drop:
                        df.loc[drop, 'base_label'] = 0

    df['block'] = (df['base_label'] != df['base_label'].shift()).cumsum()
    df['final_label'] = 0
    for _, group in df[df['base_label'] == 1].groupby('block'):
        if len(group) == 3 and group.iloc[1]['fuel'] == 0.0:
            df.loc[group.index, 'final_label'] = 1
        else:
            df.loc[group.index, 'final_label'] = 2
    return df


def resample_ign_on(df):
    """5-минутные бины. Класс 1 — заправка на ходу, класс 2 — событие с заглушенным двигателем."""
    d = df.dropna(subset=['ts']).sort_values('ts').set_index('ts')
    rows = []
    for name, group in d.resample('5min'):
        if group.empty:
            continue
        valid = group[group['raw'] > 1.0]['fuel']
        avg_fuel = valid.mean() if not valid.empty else 0.0
        has_on = (group['final_label'] == 2).any()
        has_off = (group['final_label'] == 1).any()
        base = 1 if has_on else (2 if has_off else 0)
        rows.append({
            'ts': name,
            'fuel': avg_fuel,
            'ign': group['ign'].mean(),
            'speed': group['speed'].mean(),
            'n_msg': len(group),
            'base_label': base,
        })

    res = pd.DataFrame(rows).reset_index(drop=True)
    if res.empty:
        return res

    n = len(res)
    changed = True
    while changed:                       # расширяем метку, пока уровень растёт
        changed = False
        for i in range(n):
            lbl = res.at[i, 'base_label']
            if lbl in (1, 2):
                if i > 0 and res.at[i - 1, 'base_label'] == 0:
                    if res.at[i, 'fuel'] > res.at[i - 1, 'fuel']:
                        res.at[i - 1, 'base_label'] = lbl
                        changed = True
                if i < n - 1 and res.at[i + 1, 'base_label'] == 0:
                    if res.at[i + 1, 'fuel'] > res.at[i, 'fuel']:
                        res.at[i + 1, 'base_label'] = lbl
                        changed = True

    res['block'] = (res['base_label'] != res['base_label'].shift()).cumsum()
    for _, group in res[res['base_label'].isin([1, 2])].groupby('block'):
        idx = group.index.tolist()
        if not idx:
            continue
        start = idx[0]
        while start <= idx[-1]:          # обрезаем края, которые не растут
            if start > 0 and res.at[start, 'fuel'] <= res.at[start - 1, 'fuel']:
                res.at[start, 'base_label'] = 0
                start += 1
            else:
                break
        end = idx[-1]
        while end >= start:
            if end > 0 and res.at[end, 'fuel'] <= res.at[end - 1, 'fuel']:
                res.at[end, 'base_label'] = 0
                end -= 1
            else:
                break

    res['label'] = res['base_label']
    return res[['ts', 'fuel', 'ign', 'speed', 'n_msg', 'label']]


def count_events(labels):
    """Число блоков класса 1."""
    arr = np.asarray(labels) == 1
    padded = np.pad(arr, (1, 1), constant_values=False)
    return len(np.where(np.diff(padded))[0]) // 2


# --------------------------------------------------------------------------
sessions = pd.read_sql("select id, filename from upload_session order by id", con)
sessions['unit'] = sessions['filename'].str.extract(r'(\d+)')[0]
sessions = sessions.sort_values('unit').reset_index(drop=True)
sessions['vehicle'] = [f"V{i + 1:02d}" for i in range(len(sessions))]
vmap = dict(zip(sessions['id'], sessions['vehicle']))
print(f"сессий: {len(sessions)}")

binned, raw_parts = {}, []

for sid in sorted(sessions['id'], reverse=True):     # тот же порядок, что в проде
    q = """select message_time, sensor2_raw, sensor2_smoothed, ignition, speed, original_label, label
           from track_point where session_id=? order by message_time"""
    pts = pd.read_sql(q, con, params=(sid,), parse_dates=['message_time'])
    if pts.empty:
        continue

    lbl = pts['original_label'].fillna(pts['label']).fillna('').str.lower()
    df = pd.DataFrame({
        'ts': pts['message_time'],
        'fuel': pts['sensor2_smoothed'].fillna(0.0),
        'raw': pts['sensor2_raw'].fillna(pts['sensor2_smoothed']).fillna(0.0),
        'ign': pts['ignition'].fillna(0.0),
        'speed': pts['speed'].fillna(0.0),
        'db_label': np.where(lbl.str.contains('fill|заправка'), 'fill', 'neutral'),
    })

    raw_parts.append(pd.DataFrame({
        'vehicle': vmap[sid],
        'ts': df['ts'],
        'fuel_raw': df['raw'].round(2),
        'fuel_l': df['fuel'].round(3),
        'ign': df['ign'].astype('int8'),
        'speed': df['speed'].round(1),
        'marked': (df['db_label'] == 'fill').astype('int8'),
    }))

    collapsed = collapse_zero_zones(df)
    labeled = apply_labels(collapsed)
    res = resample_ign_on(labeled)
    if res.empty:
        continue
    res.insert(0, 'vehicle', vmap[sid])
    binned[sid] = res
    print(f"  {vmap[sid]} (session {sid}): {len(pts)} сообщений -> {len(res)} бинов, "
          f"событий {count_events(res['label'])}")

# ------------------------------------------------- разбиение по ТС, как в проде
stats = [{'sid': sid, 'events': count_events(d['label'])} for sid, d in binned.items()]
stats.sort(key=lambda x: x['events'], reverse=True)
total_events = sum(s['events'] for s in stats)
target = total_events * TEST_RATIO
cap = int(len(stats) * TEST_RATIO * 1.5)

test_sids, train_sids, acc = [], [], 0
for s in stats:
    if acc < target and len(test_sids) < cap:
        test_sids.append(s['sid'])
        acc += s['events']
    else:
        train_sids.append(s['sid'])

print(f"\nсобытий всего: {total_events}; train ТС: {len(train_sids)}, test ТС: {len(test_sids)}")
print(f"событий в test: {acc}")

frames = []
for sid, d in binned.items():
    d = d.copy()
    d['split'] = 'test' if sid in test_sids else 'train'
    frames.append(d)

data = pd.concat(frames).sort_values(['vehicle', 'ts']).reset_index(drop=True)
data['fuel'] = data['fuel'].round(3)
data['ign'] = data['ign'].round(3)
data['speed'] = data['speed'].round(2)

path = os.path.join(OUT, 'fuel_5min.csv')
data.to_csv(path, index=False)
print(f"\n{path}: {len(data)} строк, {os.path.getsize(path) / 1e6:.1f} MB")
print(data['label'].value_counts().sort_index().to_string())
n_windows = sum(max(0, len(d) - SEQ_LEN + 1) for d in binned.values())
print(f"окон длины {SEQ_LEN}: {n_windows}")

raw = pd.concat(raw_parts).sort_values(['vehicle', 'ts']).reset_index(drop=True)
raw_path = os.path.join(OUT, 'fuel_raw.csv.gz')
raw.to_csv(raw_path, index=False, compression='gzip')
print(f"{raw_path}: {len(raw)} строк, {os.path.getsize(raw_path) / 1e6:.1f} MB")
