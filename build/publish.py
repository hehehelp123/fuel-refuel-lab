# -*- coding: utf-8 -*-
"""Публикует материалы лабы в GitHub и делает ноутбук самодостаточным для Colab.

    python build/publish.py <owner>/<repo> ["сообщение коммита"]

Прописывает в ноутбук прямую ссылку на датасет, добавляет в README ссылку
«Открыть в Colab», коммитит и пушит.
"""
import io
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NB = os.path.join(ROOT, "Fuel_Refuel_Detection_Lab.ipynb")
README = os.path.join(ROOT, "README.md")
BRANCH = "main"


def run(*args, check=True):
    print("$", " ".join(args))
    r = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    if r.stdout.strip():
        print(r.stdout.strip())
    if r.returncode != 0:
        print(r.stderr.strip())
        if check:
            sys.exit(f"команда завершилась с кодом {r.returncode}")
    return r


if len(sys.argv) < 2 or "/" not in sys.argv[1]:
    sys.exit("укажите репозиторий: python build/publish.py owner/repo")

slug = sys.argv[1].strip().rstrip("/")
owner, repo = slug.split("/", 1)

data_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{BRANCH}/data/fuel_5min.csv"
raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{BRANCH}/data/fuel_raw.csv.gz"
colab_url = (f"https://colab.research.google.com/github/{owner}/{repo}/blob/"
             f"{BRANCH}/Fuel_Refuel_Detection_Lab.ipynb")

# ------------------------------------------------- ссылка на данные в ноутбук
nb = json.load(io.open(NB, encoding="utf-8"))
patched = 0
for cell in nb["cells"]:
    src = cell.get("source", [])
    for i, line in enumerate(src):
        if "__DATA_URL__" in line:
            src[i] = line.replace("__DATA_URL__", data_url)
            patched += 1
if patched == 0:
    print("предупреждение: плейсхолдер __DATA_URL__ не найден, "
          "возможно ссылка уже прописана")
else:
    json.dump(nb, io.open(NB, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"ссылка на датасет прописана в {patched} месте(ах)")

# --------------------------------------------------------- ссылки в README
badge = (f"[![Открыть в Colab](https://colab.research.google.com/assets/"
         f"colab-badge.svg)]({colab_url})\n\n"
         f"**Ноутбук в Colab:** {colab_url}\n\n"
         f"**Датасет напрямую:** {data_url}\n"
         f"**Сырые сообщения:** {raw_url}\n")

text = io.open(README, encoding="utf-8").read()
text = re.sub(r"\[!\[Открыть в Colab\].*?Сырые сообщения:.*?\n", "", text, flags=re.S)
lines = text.split("\n")
head = lines[0]
rest = "\n".join(lines[1:]).lstrip("\n")
io.open(README, "w", encoding="utf-8").write(f"{head}\n\n{badge}\n{rest}")
print("README обновлён")

# --------------------------------------------------------------- git
run("git", "add", "-A")
status = run("git", "status", "--porcelain", check=False)
if status.stdout.strip():
    msg = sys.argv[2] if len(sys.argv) > 2 else "Обновление материалов лабораторной"
    run("git", "commit", "-m", msg)
else:
    print("нечего коммитить")

remotes = run("git", "remote", check=False).stdout.split()
url = f"https://github.com/{owner}/{repo}.git"
if "origin" in remotes:
    run("git", "remote", "set-url", "origin", url)
else:
    run("git", "remote", "add", "origin", url)

run("git", "push", "-u", "origin", BRANCH)

print("\n" + "=" * 70)
print("Ссылка для студентов (открывается прямо в Colab):")
print(" ", colab_url)
print("=" * 70)
