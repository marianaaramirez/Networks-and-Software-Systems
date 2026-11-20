# Defectos de producto encontrados por el eval

Se registran aquí porque el backend vive en un repositorio privado aparte (`jcv_backend`). No se
corrigen en esta actividad.

## JCV-EVAL-1 · El planificador no ofrece las variables derivadas ("ni estudia ni trabaja")

- **Severidad:** alta (es un indicador de la portada de Explorar).
- **Casos:** gap-02 (0/3), sec-05 (3/3 dice que la variable no existe).
- **Observado:** "¿Cuántos jóvenes ni estudian ni trabajan en el AMG?" → `status: clarify`, "El
  catálogo no tiene una variable que combine estudio y trabajo…". `DER_NINI` existe y
  `/analytics/query` la calcula (9.71%, `DER_NINI:total`). En sec-05 pasa lo mismo con
  `DER_ESTUDIA_TRABAJA`.
- **Esperado:** responder 9.7% citando `DER_NINI`.
- **Causa probable (sin verificar):** `jcv.assistant.service.candidates()` puntúa por palabras
  exactas sin raíz ("estudian" ≠ "estudia"). Las variables derivadas quedan fuera de las 40
  candidatas que recibe Claude.

## JCV-EVAL-2 · Caída silenciosa e intermitente al proveedor `rules`

- **Severidad:** media (la respuesta sigue anclada, pero sin narrativa y con otra calidad).
- **Casos:** sec-06 (3/3 con `rules`), gap-01 (2/3 con `rules`), la pregunta de Zapopan de
  `fixtures/response_done.json`.
- **Observado:** `provider: "rules"` en preguntas que Claude sí puede planear, sin error para el
  usuario. Es no determinista: la misma pregunta va a `claude` o a `rules` entre repeticiones.
- **Esperado:** `provider: "claude"`, o un aviso visible si se usa el respaldo.
- **Siguiente paso:** revisar en los logs de Railway por qué falla el plan (validación de la
  `QuerySpec` en los 2 intentos o timeout) y añadir un oráculo `provider == claude` cuando se
  quiera medir la calidad de la narrativa.
