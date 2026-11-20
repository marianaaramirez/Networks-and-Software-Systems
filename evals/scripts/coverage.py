"""Tablas de cobertura de evals/cases.csv por categoría, indicador, municipio, corte y año.

Uso: python3 evals/scripts/coverage.py [--base-only] > evals/results/coverage_<antes|despues>.md
"""

import csv
import sys
import unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MUNICIPIOS = {
    "el_salto": ["el salto"],
    "guadalajara": ["guadalajara", "gdl"],
    "san_pedro_tlaquepaque": ["tlaquepaque"],
    "tlajomulco_de_zuniga": ["tlajomulco"],
    "tonala": ["tonala"],
    "zapopan": ["zapopan"],
}
CORTES = {"sexo": ["mujer", "hombre", "sexo", "genero"], "edad": ["edad", "anos", "adolescent"], "estrato": ["estrato", "nivel socioeconomico"]}


def norm(t):
    return unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower()


def table(title, counter, universe=None, over=None):
    keys = list(universe) if universe else sorted(counter)
    lines = [f"### {title}", "", "| Valor | Casos | Estado |", "|---|---|---|"]
    for k in keys:
        n = counter.get(k, 0)
        state = "❌ falta" if n == 0 else ("⚠️ sobrerrepresentado" if over and n > over else "")
        lines.append(f"| {k} | {n} | {state} |")
    return "\n".join(lines) + "\n"


def main():
    base_only = "--base-only" in sys.argv
    with open(ROOT / "cases.csv", encoding="utf-8") as fh:
        cases = list(csv.DictReader(fh))
    if base_only:
        cases = [c for c in cases if c["origin"] == "ground-truth"]
    with open(ROOT / "corpus" / "corpus.csv", encoding="utf-8") as fh:
        variables = sorted({r["variable"] for r in csv.DictReader(fh)})
    cat, var, mun, corte = Counter(), Counter(), Counter(), Counter()
    for c in cases:
        cat[c["category"]] += 1
        srcs = [s for s in c["sources"].split(";") if s]
        for v in {s.split(":")[0] for s in srcs}:
            var[v] += 1
        text = norm(c["question"] + " " + c["sources"])
        for m, keys in MUNICIPIOS.items():
            if m in text or any(k in text for k in keys):
                mun[m] += 1
        for k, keys in CORTES.items():
            if f":{k}:" in c["sources"] or any(w in text for w in keys):
                corte[k] += 1
    answerable = sum(v for k, v in cat.items() if k.startswith("answerable") or k in ("paraphrase", "gap"))
    print(f"## Cobertura ({'solo ground truth' if base_only else 'conjunto completo'}) — {len(cases)} casos\n")
    print(table("Por categoría", cat, ["answerable-single", "answerable-multi", "paraphrase", "out-of-scope", "security", "gap", "regression"]))
    print(table("Por indicador (variable del corpus)", var, variables, over=max(5, answerable // 6)))
    print(table("Por municipio", mun, MUNICIPIOS))
    print(table("Por corte demográfico", corte, CORTES))
    print("### Por año\n\n| Año | Casos | Estado |\n|---|---|---|\n"
          f"| 2026 (única ola, jul-ago) | {answerable} | el corpus no tiene otros años: las preguntas de otros años van a out-of-scope |\n")


if __name__ == "__main__":
    main()
