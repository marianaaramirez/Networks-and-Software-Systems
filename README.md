# Networks-and-Software-Systems

Grupo 502 — Integration of Computer Security in Networks and Software Systems.

Mariana Ramírez Cervera (A01787819) · Juan Pablo Hernández López (A01645791) ·
Oscar Orlando de la Paz Ibarra (A01644484) · Iker Gerson Ventura Araujo (A01832672)

## Actividad: Building an Eval Set for Your AI Feature

Eval set del asistente de IA de **Jalisco Cómo Vamos** (`/api/v1/assistant/ask`).
Todo el detalle (revisión cruzada, política → oráculos, cobertura, umbrales, resultados k = 3,
análisis y huecos) está en **[evals/README.md](evals/README.md)**.

| Entregable | Ubicación |
|---|---|
| Ground truth por integrante | [`evals/ground-truth/`](evals/ground-truth/) |
| Casos fusionados y derivados | [`evals/cases.csv`](evals/cases.csv), [`evals/derived/`](evals/derived/) |
| Configuración y oráculos | [`promptfooconfig.yaml`](promptfooconfig.yaml), [`evals/oracles/oracles.js`](evals/oracles/oracles.js) |
| Reporte | [`evals/README.md`](evals/README.md) |

```bash
npm install && npm run test:oracles && npm run eval:smoke
```
