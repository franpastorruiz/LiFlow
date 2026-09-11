# Liflow

Aplicación de seguimiento personal que transforma lenguaje natural en eventos estructurados y validados.

## Estado

El proyecto comienza por el hito 1: texto → LLM → JSON → validación Pydantic → resultado listo para persistir. Cada evento admite una actividad libre y una o varias medidas controladas, como duración, distancia o gasto.

## Estructura

- `apps/api`: API backend de Liflow.
- `evals`: datasets, ejecución y resultados de evaluación del sistema de IA.
- `docs`: memoria, decisiones de arquitectura y documentación.
- `docker`: recursos de contenedorización que se incorporarán en hitos posteriores.

La memoria inicial está disponible en `docs/memoria-inicial-liflow.docx`.
