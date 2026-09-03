# -*- coding: utf-8 -*-
"""Переносит отбор лучшей эпохи с теста на валидацию."""
import io
import sys

P = "C:/Users/79101/Downloads/Лаба_заправки/build/build_notebook.py"
NL = chr(10)

PAIRS = [
    ("test_ds = TensorDataset(torch.from_numpy(X_test), torch.from_numpy(y_test))" + NL +
     "train_loader = DataLoader(train_ds, batch_size=BATCH, shuffle=True)" + NL +
     "test_loader = DataLoader(test_ds, batch_size=BATCH, shuffle=False)",

     "val_ds = TensorDataset(torch.from_numpy(X_val), torch.from_numpy(y_val))" + NL +
     "test_ds = TensorDataset(torch.from_numpy(X_test), torch.from_numpy(y_test))" + NL +
     "train_loader = DataLoader(train_ds, batch_size=BATCH, shuffle=True)" + NL +
     "val_loader = DataLoader(val_ds, batch_size=BATCH, shuffle=False)" + NL +
     "test_loader = DataLoader(test_ds, batch_size=BATCH, shuffle=False)"),

    ("    y_pred = predict(test_loader)" + NL +
     '    f1_target = f1_score(y_test, y_pred, labels=[1], average="macro", zero_division=0)' + NL +
     "    scheduler.step(f1_target)",

     "    val_pred = predict(val_loader)" + NL +
     '    f1_target = f1_score(y_val, val_pred, labels=[1], average="macro", zero_division=0)' + NL +
     "    scheduler.step(f1_target)"),

    ('          f"F1 класса 1: {f1_target:.3f}{mark}")',
     '          f"F1 на валидации: {f1_target:.3f}{mark}")'),

    ('лучший F1 класса 1: {best_f1:.3f}")',
     'лучший F1 на валидации: {best_f1:.3f}")'),

    ('print("train:", X_train.shape, "| test:", X_test.shape)',
     'print("train:", X_train.shape, "| валидация:", X_val.shape, "| test:", X_test.shape)'),

    ('print("классы в train:", np.bincount(y_train))' + NL +
     'print("классы в test :", np.bincount(y_test))',
     'print("классы в train:", np.bincount(y_train))' + NL +
     'print("классы в val  :", np.bincount(y_val))' + NL +
     'print("классы в test :", np.bincount(y_test))'),

    ("""**Про разбиение.** `split` делит выборку **по машинам, а не по точкам**.
Если резать случайно по точкам, окна одного и того же события попадут и в train, и в test,
и метрика будет завышена. Не меняйте это разбиение.""",

     """**Про разбиение.** `split` делит выборку **по машинам, а не по точкам**.
Если резать случайно по точкам, окна одного и того же события попадут и в train, и в test,
и метрика будет завышена. Не меняйте это разбиение.

Из обучающих машин мы дополнительно откладываем девять под валидацию: на ней
выбирается лучшая эпоха. Тест используется ровно один раз — для итогового замера.
Выбирать эпоху по тесту нельзя: результат окажется завышенным, а на новых машинах
модель сработает хуже, чем обещала метрика."""),
]

s = io.open(P, encoding="utf-8").read()
for old, new in PAIRS:
    if old not in s:
        sys.exit("НЕ НАЙДЕНО:" + NL + old[:200])
    s = s.replace(old, new, 1)
io.open(P, "w", encoding="utf-8").write(s)
print("готово: отбор эпохи перенесён на валидацию")
