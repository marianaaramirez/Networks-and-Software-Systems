"""Extrae el corpus de referencia (cifras ponderadas reales) desde el API público de JCV.

Cada fila es una cifra verificable: variable (= id de fuente), dataset, estadístico, corte y valor.
Los alumnos escriben su ground truth leyendo este archivo (o la app de Explorar), no al asistente.

Uso: python3 evals/scripts/build_corpus.py [--api URL]
"""

import argparse
import csv
import json
import time
import urllib.error
import unicodedata
import urllib.request
from pathlib import Path

API = "https://odoo-production-63cafea5.up.railway.app/api/v1"
OUT = Path(__file__).resolve().parents[1] / "corpus"

# variable, estadístico principal, códigos top-box, etiqueta corta
VARIABLES = [
    ("Q_6", "top_box", [4, 5], "Satisfacción con la vida (algo/muy satisfecho)"),
    ("Q_7", "top_box", [4, 5], "Calidad de vida alta (algo/muy alta)"),
    ("Q_8", "top_box", [4, 5], "Felicidad (algo/muy feliz)"),
    ("Q_10", "top_box", [4, 5], "Satisfacción con la vida afectiva"),
    ("Q_17", "top_box", [4, 5], "Educación superior: mucha/total importancia"),
    ("Q_20", "top_box", [4, 5], "Satisfacción con el tiempo libre"),
    ("Q_25", "top_box", [4, 5], "Usa chatbot de IA a diario (1 o varias veces al día)"),
    ("Q_32", "top_box", [3, 4], "Al hogar no le alcanza el ingreso"),
    ("Q_34", "top_box", [2], "Vive con familiares"),
    ("Q_35", "top_box", [1], "Se ve adquiriendo vivienda propia"),
    ("Q_37", "top_box", [4, 5], "Conseguir drogas es algo/muy fácil"),
    ("Q_41", "top_box", [4, 5], "Salud mental buena/muy buena"),
    ("Q_46", "top_box", [1, 2], "Fue víctima de algún delito (12 meses)"),
    ("Q_48", "top_box", [1], "Denunció el delito"),
    ("T_Q_43_1", "top_box", [1, 2], "Siente insegura la ciudad"),
    ("T_Q_43_2", "top_box", [1, 2], "Siente insegura su colonia"),
    ("T_Q_60_6", "top_box", [1], "Participó en colectivos"),
    ("Q_69", "top_box", [1], "Usa principalmente camión/Macrobús"),
    ("Q_70", "median", None, "Tiempo de traslado diario (mediana, minutos)"),
    ("DER_ESTUDIA_TRABAJA", "top_box", [1], "Estudia y trabaja"),
    ("DER_NINI", "top_box", [1], "Ni estudia ni trabaja"),
]
DISTRIBUTION = ["Q_6", "Q_25", "Q_32", "Q_34", "Q_38", "Q_39", "Q_41", "Q_46", "Q_69"]
BYS = [("", "Total AMG"), ("Q_2", "Municipio"), ("Q_71", "Sexo"), ("Q_72recode", "Edad"), ("Estrato", "Estrato")]


def slug(text):
    t = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode().lower()
    return "_".join("".join(c if c.isalnum() else " " for c in t).split())


def row_id(var, breakdown, group, category, stat):
    """Id de fuente estable: VARIABLE:corte:grupo[:categoria]. Ej. Q_6:municipio:zapopan."""
    key = {"Total AMG": "total", "Total Tec": "tec", "Municipio": "municipio", "Sexo": "sexo",
           "Edad": "edad", "Estrato": "estrato"}[breakdown]
    parts = [var, key] + ([] if key in ("total", "tec") else [slug(group)])
    if stat == "distribution":
        parts.append(slug(category))
    return ":".join(parts)


def post(api, path, body):
    time.sleep(0.6)  # el API limita peticiones por IP
    req = urllib.request.Request(
        api + path,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "jcv-evals/1.0"},
    )
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 3:
                time.sleep(20 * (attempt + 1))
                continue
            return {"error": e.code, "detail": e.read().decode()[:200]}
    return {"error": "retries"}


def rows_for(result, var, label, stat, by_name):
    out = []
    for s in result.get("series", []):
        group = s.get("group_label") or by_name
        if stat == "distribution":
            for p in s.get("points", []):
                out.append([row_id(var, by_name, group, p.get("label"), stat), var, label, s.get("dataset"), stat, by_name, group, p.get("label"),
                            p.get("pct"), s.get("n"), s.get("moe"), p.get("ci_low"), p.get("ci_high"), s.get("flag") or ""])
        else:
            p = (s.get("points") or [{}])[0]
            value = s.get("value") if s.get("value") is not None else p.get("pct")
            if stat == "median":
                value = s.get("median", value)
            out.append([row_id(var, by_name, group, "", stat), var, label, s.get("dataset"), stat, by_name, group, p.get("label") or "",
                        value, s.get("n"), s.get("moe"), p.get("ci_low"), p.get("ci_high"), s.get("flag") or ""])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default=API)
    args = ap.parse_args()
    header = ["source_id", "variable", "indicator", "dataset", "stat", "breakdown", "group", "category",
              "value", "n", "moe_pp", "ci_low", "ci_high", "flag"]
    rows, errors = [], []
    for var, stat, codes, label in VARIABLES:
        measure = {"variable": var, "stat": stat}
        if codes:
            measure["top_box_codes"] = codes
        for by, by_name in BYS:
            spec = {"datasets": ["amg_2026"], "measure": measure}
            if by:
                spec["by"] = by
            res = post(args.api, "/analytics/query", spec)
            if "error" in res:
                errors.append((var, by, res))
                continue
            rows += rows_for(res, var, label, stat, by_name)
        res = post(args.api, "/analytics/query", {"datasets": ["tec_2026"], "measure": measure})
        if "error" not in res:
            rows += rows_for(res, var, label, stat, "Total Tec")
    for var in DISTRIBUTION:
        res = post(args.api, "/analytics/query", {"datasets": ["amg_2026"], "measure": {"variable": var, "stat": "distribution"}})
        if "error" in res:
            errors.append((var, "dist", res))
            continue
        rows += rows_for(res, var, res.get("title", var)[:80], "distribution", "Total AMG")
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / "corpus.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)
    print(f"{len(rows)} filas → {OUT / 'corpus.csv'}")
    for e in errors:
        print("ERROR", e)


if __name__ == "__main__":
    main()
