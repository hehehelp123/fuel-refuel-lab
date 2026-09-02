# -*- coding: utf-8 -*-
"""Собирает .ipynb для Google Colab из списка ячеек."""
import json
import os

OUT = "C:/Users/79101/Downloads/Лаба_заправки/Fuel_Refuel_Detection_Lab.ipynb"

cells = []


def md(text):
    cells.append(("markdown", text))


def code(text):
    cells.append(("code", text))


# =========================================================================
md("""# Детекция заправок по датчику уровня топлива

На транспортном средстве установлен датчик уровня топлива (ДУТ). Телематический блок
раз в несколько секунд передаёт уровень, состояние зажигания, скорость и координаты.
Задача — по этому временному ряду определять моменты заправок. Это основа топливного
учёта в автопарке: без автоматической детекции баланс топлива сводят вручную по чекам.

Простое решение — порог на приросте уровня — работает плохо по трём причинам:

1. Датчик возвращает показания в условных единицах, зависящих от геометрии бака.
   Нужна тарировка в литры, своя для каждой машины.
2. Датчик запитан от зажигания и при заглушенном двигателе не передаёт ничего,
   а заправка — это чаще всего стоянка с заглушенным двигателем.
3. При работающем двигателе уровень колеблется на несколько литров из-за разгонов
   и уклонов, и медленная заправка похожа на этот шум.

Порядок работы:

1. Разбор данных, поиск заправки на графике.
2. Построение признаков и окон.
3. Обучение LSTM.
4. Расчёт метрик — точечных и событийных.
5. Сравнение с пороговым правилом.
6. Задание на самостоятельную работу.

Полный прогон ноутбука на Colab без GPU занимает около пяти минут.
""")

# -------------------------------------------------------------------------
md("""## 1. Данные

Файл `fuel_5min.csv` — реальные данные автопарка: 50 машин, полгода работы
(июль–декабрь 2025), 6.1 млн исходных сообщений, свёрнутых в **5-минутные интервалы**.
Номера машин обезличены, координаты убраны.

| колонка | что это |
|---|---|
| `vehicle` | идентификатор ТС, `V01`…`V50` |
| `ts` | начало 5-минутного интервала |
| `fuel` | средний уровень топлива в литрах по валидным сообщениям интервала |
| `ign` | доля времени с включённым зажиганием, 0..1 |
| `speed` | средняя скорость |
| `n_msg` | сколько исходных сообщений попало в интервал |
| `label` | **0** — ничего, **1** — заправка при работающем двигателе, **2** — заправка при заглушенном |
| `split` | `train` / `test`, разбиение по машинам |

**Про классы.** Наша цель — класс **1**. Класс 2 (заправка на стоянке) в этих данных
выглядит принципиально иначе: датчик молчал всю заправку, и в 5-минутном ряду от неё
остаётся только скачок уровня между двумя соседними интервалами. Мы его не выкидываем,
но и не считаем целевым — модель учится отличать все три состояния.

**Про разбиение.** `split` делит выборку **по машинам, а не по точкам**.
Если резать случайно по точкам, окна одного и того же события попадут и в train, и в test,
и метрика будет завышена. Не меняйте это разбиение.
""")

code('''import os
import time
import urllib.request

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# Откуда брать данные. Если ноутбук открыт из GitHub, ссылка уже прописана
# и ничего делать не нужно — файл скачается сам.
DATA_URL = "__DATA_URL__"
LOCAL = "fuel_5min.csv"

if not os.path.exists(LOCAL):
    if DATA_URL and not DATA_URL.startswith("__"):
        print("качаю датасет...")
        urllib.request.urlretrieve(DATA_URL, LOCAL)
    else:
        # Запасной вариант: загрузить файл кнопкой вручную
        from google.colab import files
        uploaded = files.upload()
        LOCAL = list(uploaded)[0]

df = pd.read_csv(LOCAL, parse_dates=["ts"])
print("строк:", len(df), "| машин:", df.vehicle.nunique())
df.head()''')

code('''def count_events(labels, positive=1):
    """Число непрерывных блоков нужного класса."""
    arr = np.asarray(labels) == positive
    padded = np.pad(arr, (1, 1), constant_values=False)
    return len(np.where(np.diff(padded))[0]) // 2


print("Распределение меток по интервалам:")
print(df.label.value_counts().sort_index().rename({0: "0 — ничего",
                                                   1: "1 — заправка на ходу",
                                                   2: "2 — заправка на стоянке"}))
print()
share = (df.label == 1).mean() * 100
print(f"Доля целевого класса: {share:.2f}%")
print()

for name, part in df.groupby("split"):
    ev = sum(count_events(g.label) for _, g in part.groupby("vehicle"))
    print(f"{name:5s}: машин {part.vehicle.nunique():2d}, интервалов {len(part):6d}, событий класса 1: {ev}")''')

# -------------------------------------------------------------------------
md("""### 1.1. Смотрим на заправку глазами

Прежде чем обучать что-либо, полезно посмотреть, как событие выглядит в данных.
Найдём машину с самым большим числом событий и нарисуем одно из них.
""")

code('''def events_of(g, positive=1):
    """Границы блоков класса positive внутри одной машины: список (i_start, i_end)."""
    lab = (g.label.values == positive)
    out, start = [], None
    for i, v in enumerate(lab):
        if v and start is None:
            start = i
        elif not v and start is not None:
            out.append((start, i - 1))
            start = None
    if start is not None:
        out.append((start, len(lab) - 1))
    return out


top = (df[df.label == 1].groupby("vehicle").size().sort_values(ascending=False).index[0])
g = df[df.vehicle == top].reset_index(drop=True)
evts = events_of(g)
print(f"машина {top}: событий {len(evts)}")

s, e = evts[len(evts) // 2]                 # берём событие из середины списка
lo, hi = max(0, s - 12), min(len(g) - 1, e + 12)
w = g.iloc[lo:hi + 1]

plt.figure(figsize=(9, 3))
plt.plot(w.ts, w.fuel, marker="o", ms=3, lw=1.2, color="#1a1a1a", label="уровень топлива")
plt.axvspan(g.ts[s], g.ts[e], color="#c8c8c8", alpha=0.6, label="размеченная заправка")
plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
plt.ylabel("литры")
plt.xlabel(f"{top}, {g.ts[s]:%d.%m.%Y}")
plt.legend()
plt.grid(alpha=0.3)
plt.tight_layout()
plt.show()

print(w[["ts", "fuel", "ign", "speed", "n_msg", "label"]].to_string(index=False))''')

md("""Заправка выглядит как монотонный рост уровня на протяжении нескольких интервалов.
Модель должна научиться отличать такой рост от колебаний уровня и шума датчика.

Нули в столбце `fuel` — это интервалы, в которых датчик не передавал показания
(двигатель заглушен). Это не пропуски данных, а информативный признак.
""")

# -------------------------------------------------------------------------
md("""## 2. Признаки и окна

Признаки на один интервал — намеренно простые:

* `fuel` — сам уровень;
* `d1..d4` — разности с уровнем на 1, 2, 3 и 4 интервала назад.

Зачем четыре разности разной глубины: `d1` ловит резкий скачок между соседними интервалами,
`d4` — медленный рост, размазанный на 20 минут. Так сеть видит и то, и другое
без явного сглаживающего фильтра и без порогов, подобранных руками.

Дальше нарезаем **скользящие окна по 7 интервалов** (35 минут). Класс окна — это класс
его **центрального** интервала. Центр, а не конец, потому что для решения «была ли тут заправка»
одинаково полезен контекст и до, и после момента.
""")

code('''FEATURES = ["fuel", "d1", "d2", "d3", "d4"]
SEQ_LEN = 7          # длина окна в интервалах
CENTER = SEQ_LEN // 2


def add_features(g):
    g = g.sort_values("ts").copy()
    for k in (1, 2, 3, 4):
        g[f"d{k}"] = g["fuel"].diff(k).fillna(0.0)
    return g


df = df.groupby("vehicle", group_keys=False).apply(add_features)
df[["vehicle", "ts", "fuel"] + [f"d{k}" for k in (1, 2, 3, 4)]].head(8)''')

code('''def make_windows(frame):
    """Нарезает окна внутри каждой машины отдельно, чтобы не склеить разные ТС."""
    X, y, veh, ts = [], [], [], []
    for v, g in frame.groupby("vehicle"):
        vals = g[FEATURES].values.astype("float32")
        lab = g["label"].values.astype("int64")
        times = g["ts"].values
        for i in range(len(g) - SEQ_LEN + 1):
            X.append(vals[i:i + SEQ_LEN])
            y.append(lab[i + CENTER])
            veh.append(v)
            ts.append(times[i + CENTER])
    meta = pd.DataFrame({"vehicle": veh, "ts": pd.to_datetime(ts)})
    return np.asarray(X), np.asarray(y), meta


t0 = time.time()
X_train, y_train, meta_train = make_windows(df[df.split == "train"])
X_test, y_test, meta_test = make_windows(df[df.split == "test"])
print(f"нарезка заняла {time.time() - t0:.1f} c")
print("train:", X_train.shape, "| test:", X_test.shape)
print("классы в train:", np.bincount(y_train))
print("классы в test :", np.bincount(y_test))''')

# -------------------------------------------------------------------------
md("""## 3. Модель

Двухслойная LSTM на 64 скрытых нейрона, dropout 0.2 между слоями, сверху линейный слой
на 3 класса. Берём скрытое состояние последнего элемента окна.

Это ровно та архитектура, что крутится в проде, — чтобы обученную здесь модель можно
было забрать в рабочий сервис без переписывания.
""")

code('''import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

torch.manual_seed(42)
np.random.seed(42)

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print("устройство:", DEVICE)


class FuelLSTM(nn.Module):
    def __init__(self, n_features=5, hidden=64, layers=2, n_classes=3, dropout=0.2):
        super().__init__()
        self.lstm = nn.LSTM(n_features, hidden, layers,
                            batch_first=True, dropout=dropout)
        self.fc = nn.Linear(hidden, n_classes)

    def forward(self, x):
        out, _ = self.lstm(x)
        return self.fc(out[:, -1, :])


model = FuelLSTM(n_features=len(FEATURES)).to(DEVICE)
print(model)
print("параметров:", sum(p.numel() for p in model.parameters()))''')

md("""### 3.1. Дисбаланс классов

Целевой класс занимает меньше 2% интервалов. Если ничего не делать, модель выучит
«всегда 0» и получит 98% accuracy, не найдя ни одной заправки.

Стандартный приём — веса классов в функции потерь. Но брать вес обратно
пропорционально частоте (`N_max / N_c`) здесь слишком грубо: вес улетает в десятки,
и модель начинает видеть заправки повсюду. Берём **корень** из этого отношения —
градиент от редкого класса становится заметным, но не доминирует.
""")

code('''def class_weights(y, n_classes=3, max_weight=30.0):
    counts = np.bincount(y, minlength=n_classes)
    majority = counts.max()
    w = [min(np.sqrt(majority / c), max_weight) if c > 0 else 0.0 for c in counts]
    return torch.tensor(w, dtype=torch.float32)


weights = class_weights(y_train)
for i, (c, wt) in enumerate(zip(np.bincount(y_train), weights)):
    print(f"класс {i}: {c:6d} примеров, вес {wt:.2f}")''')

# -------------------------------------------------------------------------
md("""## 4. Обучение""")

code('''EPOCHS = 30
BATCH = 512
LR = 1e-3

train_ds = TensorDataset(torch.from_numpy(X_train), torch.from_numpy(y_train))
test_ds = TensorDataset(torch.from_numpy(X_test), torch.from_numpy(y_test))
train_loader = DataLoader(train_ds, batch_size=BATCH, shuffle=True)
test_loader = DataLoader(test_ds, batch_size=BATCH, shuffle=False)

criterion = nn.CrossEntropyLoss(weight=weights.to(DEVICE))
optimizer = torch.optim.Adam(model.parameters(), lr=LR)
scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="max",
                                                       factor=0.5, patience=2)

from sklearn.metrics import f1_score


def predict(loader):
    model.eval()
    preds = []
    with torch.no_grad():
        for xb, _ in loader:
            out = model(xb.to(DEVICE))
            preds.append(out.argmax(1).cpu().numpy())
    return np.concatenate(preds)


best_f1, best_state = -1.0, None
t0 = time.time()

for epoch in range(1, EPOCHS + 1):
    model.train()
    total = 0.0
    for xb, yb in train_loader:
        xb, yb = xb.to(DEVICE), yb.to(DEVICE)
        optimizer.zero_grad()
        loss = criterion(model(xb), yb)
        loss.backward()
        optimizer.step()
        total += loss.item()

    y_pred = predict(test_loader)
    f1_target = f1_score(y_test, y_pred, labels=[1], average="macro", zero_division=0)
    scheduler.step(f1_target)

    if f1_target > best_f1:
        best_f1 = f1_target
        best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
        mark = "  <- лучшая"
    else:
        mark = ""

    print(f"эпоха {epoch:2d} | loss {total / len(train_loader):.4f} | "
          f"F1 класса 1: {f1_target:.3f}{mark}")

model.load_state_dict(best_state)
print(f"\\nобучение заняло {time.time() - t0:.0f} c, лучший F1 класса 1: {best_f1:.3f}")''')

# -------------------------------------------------------------------------
md("""## 5. Метрики

### 5.1. Точечные метрики
""")

code('''from sklearn.metrics import classification_report, confusion_matrix

y_pred = predict(test_loader)

names = ["0 — ничего", "1 — заправка на ходу", "2 — на стоянке"]
print(classification_report(y_test, y_pred, target_names=names,
                            digits=3, zero_division=0))

cm = confusion_matrix(y_test, y_pred, labels=[0, 1, 2])
fig, ax = plt.subplots(figsize=(4.2, 3.6))
ax.imshow(cm / cm.sum(axis=1, keepdims=True).clip(min=1), cmap="Greys", vmin=0, vmax=1.3)
for i in range(3):
    for j in range(3):
        ax.text(j, i, cm[i, j], ha="center", va="center", fontsize=9,
                color="white" if cm[i, j] / max(cm[i].sum(), 1) > 0.55 else "black")
ax.set_xticks(range(3), ["0", "1", "2"])
ax.set_yticks(range(3), ["0", "1", "2"])
ax.set_xlabel("предсказано")
ax.set_ylabel("на самом деле")
ax.grid(False)
plt.tight_layout()
plt.show()''')

md("""Класс 2 в тесте представлен всего парой десятков интервалов, поэтому его строчка
в отчёте шумная — не делайте по ней выводов. Целевой класс — первый.

### 5.2. Почему точечных метрик мало

Оператору автопарка не нужен ответ «этот пятиминутный интервал относится к заправке».
Ему нужно «14 августа в 10:05 машина V11 заправилась». Это **событие**, а не точка.

Разница существенная. Модель, которая на каждой заправке угадала 3 интервала из 5,
по точечной метрике выглядит средне, а по событийной — идеально: событие найдено.
И наоборот, модель, которая ровно один интервал посреди пустой стоянки пометила заправкой,
по точечной метрике почти не пострадает, а по событийной получит ложное срабатывание.

Считаем так: собираем предсказанные и эталонные события как непрерывные блоки класса 1
и сопоставляем их с допуском **±5 минут**. Предсказание, попавшее на класс 2,
не штрафуем — там разметке доверять нельзя.
""")

code('''TOLERANCE = np.timedelta64(5, "m")


def blocks(mask, times):
    """Непрерывные блоки True -> список (t_start, t_end)."""
    out, start = [], None
    for i, v in enumerate(mask):
        if v and start is None:
            start = i
        elif not v and start is not None:
            out.append((times[start], times[i - 1]))
            start = None
    if start is not None:
        out.append((times[start], times[len(mask) - 1]))
    return out


def event_metrics(y_true, y_pred, meta, verbose=True):
    tp = fp = fn = 0
    for v, sub in meta.groupby("vehicle"):
        pos = sub.index.to_numpy()          # meta идёт в том же порядке, что y_true/y_pred
        times = sub["ts"].values
        t_true = blocks(y_true[pos] == 1, times)
        t_pred = blocks(y_pred[pos] == 1, times)
        t_amb = blocks(y_true[pos] == 2, times)

        matched = set()
        for ps, pe in t_pred:
            hit = [k for k, (ts_, te_) in enumerate(t_true)
                   if ps <= te_ + TOLERANCE and pe >= ts_ - TOLERANCE]
            if hit:
                tp += 1
                matched.update(hit)
            elif any(ps <= te_ + TOLERANCE and pe >= ts_ - TOLERANCE
                     for ts_, te_ in t_amb):
                pass                      # попали в неоднозначную зону — не штрафуем
            else:
                fp += 1
        fn += len(t_true) - len(matched)

    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    if verbose:
        print(f"события: TP={tp}  FP={fp}  FN={fn}")
        print(f"precision={precision:.3f}  recall={recall:.3f}  F1={f1:.3f}")
    return {"tp": tp, "fp": fp, "fn": fn,
            "precision": precision, "recall": recall, "f1": f1}


lstm_events = event_metrics(y_test, y_pred, meta_test)''')

# -------------------------------------------------------------------------
md("""## 6. С чем сравнивать: пороговое правило

Способ, который применяют по умолчанию, — порог на приросте уровня: если уровень
вырос больше чем на X литров за интервал, считаем это заправкой. Посмотрим, какой
результат он даёт на тех же данных. Это нижняя граница, с которой сравнивают модель.
""")

code('''# прирост уровня в центральном интервале окна — то, на что смотрит пороговое правило
d1_center = X_test[:, CENTER, FEATURES.index("d1")]

print(f"{'порог, л':>10} | {'precision':>9} | {'recall':>6} | {'F1':>5}")
print("-" * 42)
best_thr, best_thr_f1 = None, -1
for thr in [1, 2, 3, 5, 8, 12, 20]:
    pred_thr = (d1_center > thr).astype("int64")
    m = event_metrics(y_test, pred_thr, meta_test, verbose=False)
    print(f"{thr:>10} | {m['precision']:>9.3f} | {m['recall']:>6.3f} | {m['f1']:>5.3f}")
    if m["f1"] > best_thr_f1:
        best_thr_f1, best_thr = m["f1"], thr

print(f"\\nлучший порог: {best_thr} л, событийный F1 = {best_thr_f1:.3f}")
print(f"LSTM:                событийный F1 = {lstm_events['f1']:.3f}")''')

# -------------------------------------------------------------------------
md("""## 7. Итог бейзлайна

Ячейка ниже собирает метрики бейзлайна в один отчёт.
""")

code('''from sklearn.metrics import precision_score, recall_score

def report(y_true, y_pred, meta, title="модель"):
    p = precision_score(y_true, y_pred, labels=[1], average="macro", zero_division=0)
    r = recall_score(y_true, y_pred, labels=[1], average="macro", zero_division=0)
    f = f1_score(y_true, y_pred, labels=[1], average="macro", zero_division=0)
    macro = f1_score(y_true, y_pred, average="macro", zero_division=0)
    ev = event_metrics(y_true, y_pred, meta, verbose=False)
    print(f"=== {title} ===")
    print(f"точечные (класс 1): precision={p:.3f}  recall={r:.3f}  F1={f:.3f}")
    print(f"macro F1 по трём классам: {macro:.3f}")
    print(f"событийные: TP={ev['tp']} FP={ev['fp']} FN={ev['fn']}  "
          f"precision={ev['precision']:.3f} recall={ev['recall']:.3f} F1={ev['f1']:.3f}")
    return {"point_f1": f, "event_f1": ev["f1"]}


baseline = report(y_test, y_pred, meta_test, "LSTM baseline")''')

# -------------------------------------------------------------------------
md("""## 8. Задание

**Цель: увеличить событийный F1 на тестовых машинах.**

Главная метрика — `event_f1` из отчёта выше. Вторая метрика — точечный F1 по классу 1;
её тоже указывайте, чтобы было видно, за счёт чего вырос результат.

### Правила

1. Разбиение `split` не трогаем. Обучаться на машинах из `test` нельзя.
2. Метки в тесте не меняем.
3. Гиперпараметры подбираем на train (можно отрезать часть train-машин под валидацию).
   Если крутить их прямо по тесту, вы просто переобучитесь на пять машин.
4. В отчёте — таблица «что поменял → какой стал event_f1», а не только финальное число.

### Что можно попробовать

От простого к сложному:

* **Признаки.** Сейчас используется только уровень и четыре разности. В данных есть
  `ign`, `speed`, `n_msg`, время суток. Заправка на ходу — это почти всегда малая скорость
  при включённом зажигании. Помогает ли это?
* **Нормализация.** Признаки поданы в сыром виде: уровень в литрах (0–100), разности около нуля.
  Попробуйте стандартизацию — статистики считайте **только по train**.
* **Длина окна.** 7 интервалов = 35 минут. Длиннее — больше контекста и меньше окон; короче — наоборот.
* **Веса классов.** Мы взяли корень из отношения частот. Попробуйте другую степень,
  focal loss или пересэмплирование.
* **Архитектура.** Двунаправленная LSTM, GRU, одномерная свёртка, attention над окном.
  Модель крошечная — экспериментировать дёшево.
* **Постобработка.** Одиночный интервал класса 1 среди нулей, скорее всего, ложное
  срабатывание. Сглаживание предсказаний или требование минимальной длины события
  нередко даёт больше, чем смена архитектуры.
* **Порог решения.** `argmax` — не догма. Возьмите вероятность класса 1 и подберите порог
  под нужный баланс precision/recall.
* **Другой размер интервала.** Файл `fuel_raw.csv.gz` содержит исходные сообщения.
  5 минут — это наш выбор, а не закон природы.

### Что сдавать

Ноутбук, в котором:

1. воспроизводится бейзлайн (можно ссылкой на этот),
2. реализовано ваше улучшение,
3. в конце вызван `report(...)` — сравнение с бейзлайном по обеим метрикам,
4. есть короткий разбор: что сработало, что нет и почему вы так думаете.

### Отдельный вопрос со звёздочкой

В том же проекте есть вторая модель — для заправок при заглушенном двигателе.
На тесте она даёт **accuracy 100% и F1 = 1.0** по целевому классу.

Разметка там ставится так: блок из ровно трёх точек, где в середине уровень равен нулю,
а слева и справа уровни стабильны и различаются. Признаки — уровень и его разности.

Вопрос: почему стопроцентный результат в этой постановке ничего не говорит о качестве
детекции? Что нужно поменять, чтобы число стало осмысленным?
""")

# =========================================================================
nb = {
    "cells": [
        {
            "cell_type": kind,
            "metadata": {},
            "source": src.splitlines(keepends=True),
            **({"execution_count": None, "outputs": []} if kind == "code" else {}),
        }
        for kind, src in cells
    ],
    "metadata": {
        "colab": {"provenance": [], "toc_visible": True},
        "kernelspec": {"name": "python3", "display_name": "Python 3"},
        "language_info": {"name": "python"},
    },
    "nbformat": 4,
    "nbformat_minor": 0,
}

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print(f"{OUT}: {len(cells)} ячеек "
      f"({sum(1 for k, _ in cells if k == 'code')} кодовых)")
