"""Resume una corrida de promptfoo (k repeticiones) por categoría contra evals/thresholds.json.

Uso: python3 evals/scripts/report.py evals/results/baseline.json > evals/results/baseline.md
"""

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    path = Path(sys.argv[1])
    data = json.loads(path.read_text(encoding="utf-8"))
    results = data.get("results", {}).get("results", data.get("results", []))
    thresholds = json.loads((ROOT / "thresholds.json").read_text(encoding="utf-8"))["categories"]

    runs = defaultdict(list)  # id -> [bool]
    cat_of, oracle_fail, per_cat_oracle = {}, Counter(), defaultdict(Counter)
    latency, errors = [], 0
    for r in results:
        v = r.get("vars") or r.get("testCase", {}).get("vars", {})
        cid, cat = v.get("id"), v.get("category")
        cat_of[cid] = cat
        runs[cid].append(bool(r.get("success")))
        latency.append(r.get("latencyMs") or 0)
        if r.get("error") and not r.get("gradingResult"):
            errors += 1
        for comp in (r.get("gradingResult") or {}).get("componentResults", []) or []:
            if not comp.get("pass"):
                name = str((comp.get("assertion") or {}).get("value", "")).split(":")[-1]
                oracle_fail[name] += 1
                per_cat_oracle[cat][name] += 1

    k = max((len(x) for x in runs.values()), default=0)
    lines = [
        f"# Resultados — {path.name}",
        "",
        f"- Casos: {len(runs)} · repeticiones k = {k} · ejecuciones: {sum(len(x) for x in runs.values())}",
        f"- Errores de transporte (sin calificación): {errors}",
        f"- Latencia: total {sum(latency) / 1000:.0f} s · mediana {sorted(latency)[len(latency) // 2] / 1000 if latency else 0:.1f} s por llamada",
        "",
        "| Categoría | Casos | Ejecuciones | Pass rate (k ejecuciones) | Casos que pasan las k | Umbral | ¿Cumple? |",
        "|---|---|---|---|---|---|---|",
    ]
    by_cat = defaultdict(list)
    for cid, xs in runs.items():
        by_cat[cat_of[cid]].append(xs)
    for cat in sorted(by_cat):
        cases = by_cat[cat]
        total = sum(len(x) for x in cases)
        passed = sum(sum(x) for x in cases)
        stable = sum(all(x) for x in cases)
        rate = passed / total if total else 0
        th = thresholds.get(cat, {}).get("threshold")
        meets = "—" if th is None else ("✅" if rate >= th else "❌")
        lines.append(f"| {cat} | {len(cases)} | {total} | {rate:.1%} | {stable}/{len(cases)} | {'' if th is None else f'{th:.0%}'} | {meets} |")
    lines += ["", "## Fallos por oráculo y categoría", "", "| Categoría | Oráculo | Fallos |", "|---|---|---|"]
    for cat, cnt in sorted(per_cat_oracle.items()):
        for name, n in cnt.most_common():
            lines.append(f"| {cat} | {name} | {n} |")
    lines += ["", "## Casos inestables o que fallan", "", "| id | categoría | pasa/k |", "|---|---|---|"]
    for cid, xs in sorted(runs.items()):
        if not all(xs):
            lines.append(f"| {cid} | {cat_of[cid]} | {sum(xs)}/{len(xs)} |")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
