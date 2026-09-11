# ADR 001 Trackers dinámicos y métricas personales

## Contexto

Liflow debe permitir registrar actividades diversas sin mantener una lista cerrada de actividades, métricas o unidades. Además, cada usuario podrá organizar sus registros en trackers personales, como Universidad, Entrenamiento o Finanzas.

## Decisión

Cada evento tendrá un nombre de actividad libre, una fecha y observaciones asociadas a claves de métricas. Un tracker aporta el catálogo dinámico de `MetricDefinition` que conoce el usuario. El extractor reutilizará esas claves y, si no existe una métrica adecuada, devolverá una `NewMetricProposal` independiente de la observación.

## Consecuencias

Una sesión de estudio puede reutilizar `study_duration` y `concentration`, y proponer `exercises_completed` si todavía no existe. Se pueden añadir nuevas actividades, métricas y unidades sin cambiar el esquema ni redeplegar la aplicación. La agregación y los tipos de dato se mantienen controlados porque afectan a cómo se interpretarán las estadísticas.
