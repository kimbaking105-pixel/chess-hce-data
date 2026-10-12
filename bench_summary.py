#!/usr/bin/env python3
"""Итог проверочного теста: читает bench/games_*.jsonl и bench/summary.txt."""
import glob
import json
import statistics as st
import sys

folder = sys.argv[1] if len(sys.argv) > 1 else "bench"
wall = int(open(f"{folder}/summary.txt").read().split("=")[1])
times, draws, total, timeouts = [], 0, 0, 0
for fn in glob.glob(f"{folder}/games_*.jsonl"):
    for line in open(fn):
        g = json.loads(line)
        total += 1
        times.append(g["wall_s"])
        if g["result"] == "1/2-1/2":
            draws += 1
        if g["reason"] == "time":
            timeouts += 1

print(f"партий: {total}")
print(f"среднее время партии: {st.mean(times):.1f} с (медиана {st.median(times):.1f} с)")
print(f"ничьих: {draws / total:.0%}")
print(f"проигрышей по времени: {timeouts} ({timeouts / total:.1%})")
print(f"фактическая скорость: {total / wall * 3600:.0f} партий в час на 4 процессах")
print(f"ожидание на 5000 партий: {5000 / (total / wall) / 60:.0f} мин на 4 процессах")
