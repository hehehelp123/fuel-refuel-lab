# -*- coding: utf-8 -*-
"""Прогоняет кодовые ячейки ноутбука как скрипт, чтобы проверить, что всё считается.

Подменяет только ячейку загрузки данных (в Colab там upload).
"""
import json
import sys
import time

import matplotlib
matplotlib.use("Agg")

NB = "C:/Users/79101/Downloads/Лаба_заправки/Fuel_Refuel_Detection_Lab.ipynb"
CSV = "C:/Users/79101/Downloads/Лаба_заправки/data/fuel_5min.csv"

with open(NB, encoding="utf-8") as f:
    nb = json.load(f)

cells = ["".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code"]
print(f"кодовых ячеек: {len(cells)}\n")

env = {"__name__": "__main__"}
for i, src in enumerate(cells, 1):
    if "files.upload" in src:
        src = src.replace('LOCAL = "fuel_5min.csv"', f'LOCAL = r"{CSV}"')
        src = src.replace("if not os.path.exists(LOCAL):", "if False:")
    print(f"--- ячейка {i} " + "-" * 50)
    t0 = time.time()
    try:
        exec(compile(src, f"<cell {i}>", "exec"), env)
    except Exception as exc:
        print(f"ОШИБКА в ячейке {i}: {type(exc).__name__}: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    print(f"[{time.time() - t0:.1f} c]\n")

print("все ячейки отработали")
