"""Fusiona ground truth revisado + casos derivados en evals/cases.csv y resume la revisión cruzada.

Entradas
  evals/ground-truth/<usuario>.csv   20 pares originales por alumno (no se modifican).
  evals/review/<revisor>__<autor>.csv  veredicto por id: ✓ correcto · ✎ corregido · ✗ descartado.
  evals/derived/*.csv                paráfrasis, fuera de alcance, seguridad, huecos, regresión.
  evals/corpus/corpus.csv            cifras del corpus (para validar fuentes y extraer cifras).

Salidas
  evals/cases.csv                    conjunto final (lo lee promptfooconfig.yaml).
  evals/smoke.csv                    5 casos para desarrollo barato.
  evals/results/review_summary.md    tabla de la revisión cruzada.

Uso: python3 evals/scripts/build_cases.py
"""

import csv
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GT_COLS = ["id", "question", "answer", "sources", "type", "difficulty"]
CASE_COLS = [
    "id", "category", "origin", "question", "expected_answer", "expected_figures", "sources",
    "expected_behavior", "base_id", "ai_generated", "reviewed_by", "notes",
]
NUM = re.compile(r"(?<![\w.])(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)")
STRUCTURAL = {2026.0}


def norm(text):
    t = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", t).split())


def read(path):
    with open(path, encoding="utf-8-sig", newline="") as fh:
        return [{k.strip(): (v or "").strip() for k, v in r.items() if k} for r in csv.DictReader(fh)]


def corpus():
    rows = read(ROOT / "corpus" / "corpus.csv")
    by_id = {r["source_id"]: r for r in rows}
    return by_id


def figures(answer, sources, corpus_by_id):
    """Cifras del answer que existen en las filas citadas del corpus (±0.06)."""
    allowed = []
    for sid in sources:
        row = corpus_by_id.get(sid)
        if row:
            for k in ("value", "n", "moe_pp", "ci_low", "ci_high"):
                try:
                    allowed.append(float(row[k]))
                except (ValueError, KeyError):
                    pass
    found, unknown = [], []
    for raw in NUM.findall(answer):
        n = float(raw.replace(",", ""))
        if n in STRUCTURAL:
            continue
        (found if any(abs(n - a) <= 0.06 or abs(n - round(a, 1)) <= 0.06 for a in allowed) else unknown).append(raw)
    return found, unknown


def main():
    corpus_by_id = corpus()
    problems = []
    base, authors = {}, {}
    for path in sorted((ROOT / "ground-truth").glob("*.csv")):
        user = path.stem
        rows = [r for r in read(path) if r.get("question")]
        authors[user] = len(rows)
        if rows and len(rows) != 20:
            problems.append(f"{user}: {len(rows)} pares (se esperan 20)")
        for r in rows:
            base[r["id"]] = {**r, "_author": user}

    # Revisión cruzada
    review_stats = defaultdict(Counter)
    reasons = Counter()
    who = []
    for path in sorted((ROOT / "review").glob("*__*.csv")):
        reviewer, author = path.stem.split("__", 1)
        who.append((reviewer, author))
        for r in read(path):
            gid = r.get("id")
            if gid not in base:
                continue
            verdict = r.get("verdict", "")
            kind = {"✓": "ok", "✎": "fixed", "✗": "discarded"}.get(verdict, verdict or "pendiente")
            review_stats[author][kind] += 1
            if r.get("error_kind"):
                reasons[r["error_kind"]] += 1
            base[gid]["_reviewer"] = reviewer
            if kind == "fixed":
                for col in ("question", "answer", "sources", "type", "difficulty"):
                    if r.get(col):
                        base[gid][col] = r[col]
            elif kind == "discarded":
                base[gid]["_discarded"] = r.get("reason", "")

    # Casos base
    cases, seen = [], {}
    dupes = 0
    for gid, r in base.items():
        if r.get("_discarded") is not None:
            continue
        key = norm(r["question"])
        if key in seen:
            dupes += 1
            continue
        seen[key] = gid
        sources = [s.strip() for s in r["sources"].split(";") if s.strip()]
        missing = [s for s in sources if s not in corpus_by_id]
        if missing:
            problems.append(f"{gid}: fuente(s) inexistente(s) en el corpus: {', '.join(missing)}")
        found, unknown = figures(r["answer"], sources, corpus_by_id)
        if unknown:
            problems.append(f"{gid}: cifra(s) {', '.join(unknown)} no aparecen en las fuentes citadas")
        multi = len(sources) > 1 or r.get("type") in ("comparison", "trend")
        cases.append({
            "id": gid,
            "category": "answerable-multi" if multi else "answerable-single",
            "origin": "ground-truth",
            "question": r["question"],
            "expected_answer": r["answer"],
            "expected_figures": ";".join(found),
            "sources": ";".join(sources),
            "expected_behavior": "answer",
            "base_id": "",
            "ai_generated": "no",
            "reviewed_by": r.get("_reviewer", ""),
            "notes": f"{r.get('type', '')} · {r.get('difficulty', '')}",
        })
    by_id = {c["id"]: c for c in cases}

    # Derivados
    for path in sorted((ROOT / "derived").glob("*.csv")):
        for r in read(path):
            if not r.get("question"):
                continue
            row = {c: r.get(c, "") for c in CASE_COLS}
            if row["category"] == "paraphrase":
                src = by_id.get(row["base_id"])
                if not src:
                    problems.append(f"{row['id']}: base_id {row['base_id']} no existe o fue descartado")
                    continue
                for c in ("expected_answer", "expected_figures", "sources"):
                    row[c] = src[c]
                row["expected_behavior"] = "answer"
            if row["ai_generated"] == "yes" and not row["reviewed_by"]:
                problems.append(f"{row['id']}: generado con IA y sin revisor (reviewed_by)")
            if row["ai_generated"] == "yes" and row["reviewed_by"]:
                row["origin"] = f"{row['origin']}+ai-generated (reviewed)"
            cases.append(row)

    with open(ROOT / "cases.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=CASE_COLS)
        w.writeheader()
        w.writerows(cases)
    smoke_ids, cats = [], set()
    for c in cases:  # un caso por categoría hasta 5
        if c["category"] not in cats and len(smoke_ids) < 5:
            cats.add(c["category"])
            smoke_ids.append(c)
    with open(ROOT / "smoke.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=CASE_COLS)
        w.writeheader()
        w.writerows(smoke_ids)

    out = ["| Autor | Revisor | Pares | ✓ | ✎ | ✗ | Pendientes |", "|---|---|---|---|---|---|---|"]
    rev_of = {a: r for r, a in who}
    for author, n in authors.items():
        s = review_stats[author]
        out.append(f"| {author} | {rev_of.get(author, '—')} | {n} | {s['ok']} | {s['fixed']} | {s['discarded']} | {n - s['ok'] - s['fixed'] - s['discarded']} |")
    out += ["", f"Duplicados eliminados: {dupes}", "", "Tipos de error más comunes:"]
    out += [f"- {k}: {v}" for k, v in reasons.most_common()] or ["- (sin datos)"]
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results" / "review_summary.md").write_text("\n".join(out) + "\n", encoding="utf-8")

    print(f"{len(cases)} casos → evals/cases.csv ({Counter(c['category'] for c in cases)})")
    print("\n".join(out))
    if problems:
        print("\nPROBLEMAS A CORREGIR:")
        print("\n".join(f"- {p}" for p in problems))
        sys.exit(1 if "--strict" in sys.argv else 0)


if __name__ == "__main__":
    main()
