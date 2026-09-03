# -*- coding: utf-8 -*-
"""Проверка достижимости планки: гоняет варианты улучшений и меряет событийный F1.

Протокол честный: из 45 обучающих машин 9 откладываются под валидацию,
эпоха выбирается по валидации, тест трогается один раз на вариант.
"""
import json
import time

import matplotlib
matplotlib.use("Agg")   # иначе plt.show() в ячейках ноутбука блокирует процесс

import numpy as np
import torch
import torch.nn as nn
from sklearn.metrics import f1_score
from torch.utils.data import DataLoader, TensorDataset

NB = "C:/Users/79101/Downloads/Лаба_заправки/Fuel_Refuel_Detection_Lab.ipynb"
CSV = "C:/Users/79101/Downloads/Лаба_заправки/data/fuel_5min.csv"

# --- поднимаем окружение ноутбука, но без его собственного обучения
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
    if "for epoch in range(1, EPOCHS + 1)" in src:
        src = src.replace("EPOCHS = 30", "EPOCHS = 0")   # baseline обучим сами
        src = src.replace("model.load_state_dict(best_state)", "pass")
    exec(compile(src, "<cell>", "exec"), env)

df = env["df"]
make_windows = env["make_windows"]
event_metrics = env["event_metrics"]
FuelLSTM = env["FuelLSTM"]
DEVICE = env["DEVICE"]

# --- делим обучающие машины на подобучение и валидацию по числу событий
count_events = env["count_events"]
train_veh = sorted(df[df.split == "train"].vehicle.unique())
ev = {v: count_events(df[df.vehicle == v].label) for v in train_veh}
order = sorted(train_veh, key=lambda v: -ev[v])
val_veh = set(order[1::5][:9])                       # разрежённо, чтобы события не собрались в одну кучу
sub_veh = [v for v in train_veh if v not in val_veh]
print(f"подобучение: {len(sub_veh)} машин, валидация: {len(val_veh)}, тест: "
      f"{df[df.split == 'test'].vehicle.nunique()}")


def build(features, seq_len, binary=False):
    env["FEATURES"] = features
    env["SEQ_LEN"] = seq_len
    env["CENTER"] = seq_len // 2
    out = {}
    for name, mask in (("sub", df.vehicle.isin(sub_veh)),
                       ("val", df.vehicle.isin(val_veh)),
                       ("test", df.split == "test")):
        X, y, meta = make_windows(df[mask])
        if binary:
            y = (y > 0).astype("int64")
        out[name] = (X, y, meta)
    return out


def class_weights(y, n_classes, max_weight=30.0):
    counts = np.bincount(y, minlength=n_classes)
    maj = counts.max()
    return torch.tensor([min(np.sqrt(maj / c), max_weight) if c > 0 else 0.0
                         for c in counts], dtype=torch.float32)


class BiLSTM(nn.Module):
    def __init__(self, n_features, hidden=64, layers=2, n_classes=3, dropout=0.2):
        super().__init__()
        self.lstm = nn.LSTM(n_features, hidden, layers, batch_first=True,
                            dropout=dropout, bidirectional=True)
        self.fc = nn.Linear(hidden * 2, n_classes)

    def forward(self, x):
        out, _ = self.lstm(x)
        return self.fc(out[:, -1, :])


def smooth(pred, min_len=2):
    """Выбрасывает блоки класса 1 короче min_len."""
    pred = pred.copy()
    st = None
    for i, v in enumerate(np.append(pred == 1, False)):
        if v and st is None:
            st = i
        elif not v and st is not None:
            if i - st < min_len:
                pred[st:i] = 0
            st = None
    return pred


def run(name, features=None, seq_len=7, bidir=False, normalize=False,
        binary=False, min_len=1, prob_thr=None, epochs=30, seed=42):
    features = features or ["fuel", "d1", "d2", "d3", "d4"]
    torch.manual_seed(seed)
    np.random.seed(seed)
    data = build(features, seq_len, binary)
    n_classes = 2 if binary else 3

    Xs, ys, _ = data["sub"]
    Xv, yv, mv = data["val"]
    Xt, yt, mt = data["test"]

    if normalize:
        mu = Xs.reshape(-1, Xs.shape[-1]).mean(0)
        sd = Xs.reshape(-1, Xs.shape[-1]).std(0) + 1e-6
        Xs, Xv, Xt = [(a - mu) / sd for a in (Xs, Xv, Xt)]

    net = (BiLSTM if bidir else FuelLSTM)(len(features), n_classes=n_classes).to(DEVICE)
    opt = torch.optim.Adam(net.parameters(), lr=1e-3)
    sched = torch.optim.lr_scheduler.ReduceLROnPlateau(opt, mode="max", factor=0.5, patience=2)
    crit = nn.CrossEntropyLoss(weight=class_weights(ys, n_classes).to(DEVICE))
    loader = DataLoader(TensorDataset(torch.from_numpy(Xs), torch.from_numpy(ys)),
                        batch_size=512, shuffle=True)

    def predict(X):
        net.eval()
        outs = []
        with torch.no_grad():
            for i in range(0, len(X), 4096):
                logits = net(torch.from_numpy(X[i:i + 4096]).to(DEVICE))
                outs.append(torch.softmax(logits, 1).cpu().numpy())
        return np.concatenate(outs)

    def decide(prob):
        if prob_thr is not None:
            pred = (prob[:, 1] > prob_thr).astype("int64")
        else:
            pred = prob.argmax(1)
        return smooth(pred, min_len) if min_len > 1 else pred

    best_val, best_state = -1, None
    t0 = time.time()
    for ep in range(epochs):
        net.train()
        for xb, yb in loader:
            opt.zero_grad()
            crit(net(xb.to(DEVICE)), yb.to(DEVICE)).backward()
            opt.step()
        vp = decide(predict(Xv))
        v_f1 = event_metrics(yv, vp, mv, verbose=False)["f1"]
        sched.step(v_f1)
        if v_f1 > best_val:
            best_val = v_f1
            best_state = {k: v.cpu().clone() for k, v in net.state_dict().items()}

    net.load_state_dict(best_state)
    tp = decide(predict(Xt))
    m = event_metrics(yt, tp, mt, verbose=False)
    point = f1_score(yt, tp, labels=[1], average="macro", zero_division=0)
    print(f"{name:42s} val {best_val:.3f} | тест: событийный F1 {m['f1']:.3f} "
          f"(P {m['precision']:.3f} R {m['recall']:.3f}, TP {m['tp']} FP {m['fp']} FN {m['fn']}) "
          f"| точечный {point:.3f} | {time.time() - t0:.0f} c")
    return m["f1"]


print()
results = {}
results["база (как в ноутбуке)"] = run("база (как в ноутбуке)")
results["+ ign, speed, n_msg"] = run("+ ign, speed, n_msg",
                                     features=["fuel", "d1", "d2", "d3", "d4",
                                               "ign", "speed", "n_msg"])
results["+ нормализация"] = run("+ нормализация", normalize=True)
results["окно 11"] = run("окно 11", seq_len=11)
results["двунаправленная LSTM"] = run("двунаправленная LSTM", bidir=True)
results["постобработка: блок >= 2"] = run("постобработка: блок >= 2", min_len=2)
results["классы 1 и 2 объединены"] = run("классы 1 и 2 объединены", binary=True)
results["всё вместе"] = run("всё вместе",
                            features=["fuel", "d1", "d2", "d3", "d4",
                                      "ign", "speed", "n_msg"],
                            normalize=True, bidir=True, seq_len=9, min_len=2)

print("\n=== итог ===")
for k, v in sorted(results.items(), key=lambda x: -x[1]):
    print(f"  {v:.3f}  {k}")
