# Fase 1: ground truth individual

Cada integrante llena **su** archivo `<github-username>.csv` con 20 pares pregunta–respuesta,
**leyendo el corpus**, sin preguntarle a la app ni a un asistente de IA. Los pares que no se
puedan rastrear a una fila del corpus se descartan en la revisión.

## De dónde salen las respuestas

`evals/corpus/corpus.csv` tiene las cifras ponderadas oficiales de la Encuesta de Bienestar de
Jóvenes AMG (jul-ago 2026). Se genera desde el API público con `npm run corpus`. Cada fila es
una cifra con un id estable en la columna `source_id`:

| source_id | Qué es |
|---|---|
| `Q_6:total` | Valor del indicador para todo el AMG |
| `Q_6:municipio:zapopan` | Valor en un municipio (`el_salto`, `guadalajara`, `san_pedro_tlaquepaque`, `tlajomulco_de_zuniga`, `tonala`, `zapopan`) |
| `Q_41:sexo:mujer` | Corte por sexo (`hombre`, `mujer`) |
| `Q_6:edad:15_a_19_anos` | Corte por edad (`15_a_19_anos`, `20_a_24_anos`, `25_a_29_anos`) |
| `T_Q_43_2:estrato:bajo` | Corte por estrato (`alto`, `medio`, `bajo`) |
| `Q_69:total:camion_macrobus` | Una categoría de la distribución completa |

También pueden consultar el cuestionario y libro de códigos en `backend/data/raw/` y la pestaña
**Explorar** de la app, pero la fuente que se cita siempre es un `source_id` del corpus.

## Columnas

| Campo | Cómo llenarlo |
|---|---|
| `id` | `<iniciales>-01` … `<iniciales>-20` (ej. `MRC-07`) |
| `question` | Como la escribiría una persona joven o un periodista en la app |
| `answer` | 1–2 oraciones con la **cifra exacta** del corpus (ej. "92.3% de los jóvenes de Zapopan…") |
| `sources` | Uno o más `source_id` separados por `;` |
| `type` | `single-fact` · `comparison` · `trend` · `definition` · `other` |
| `difficulty` | `easy` / `medium` / `hard` + una palabra de por qué (ej. `medium: cruce`) |

Si un campo lleva comas, va entre comillas dobles (así lo guarda Excel o Google Sheets al exportar
como CSV UTF-8).

## Requisitos de tus 20

- Al menos **5** que necesiten más de una fuente (dos municipios, dos grupos, dos indicadores).
- Al menos **3** de tendencia o cambio. El corpus tiene **una sola ola (2026)**, así que la
  "tendencia" se toma a lo largo de la edad (15–19 → 20–24 → 25–29) o del estrato (alto → bajo).
  Escribe en `answer` la dirección y las cifras de cada punto.
- Máximo **5** sobre el mismo indicador (misma variable `Q_…`).
- Ninguna con datos personales.

## Al terminar

```bash
npm run cases     # valida fuentes y cifras; marca las cifras que no aparecen en el corpus
```

Una vez revisado, el archivo **no se vuelve a editar**: las correcciones van en
`evals/review/<revisor>__<autor>.csv`.
