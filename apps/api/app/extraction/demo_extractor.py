from app.schemas.event import LifeEvent, NewMetricProposal
from app.schemas.extraction import ExtractionRequest, ExtractionResult


class DemoExtractor:
    """Temporary deterministic extractor used before connecting an LLM."""

    def extract(self, request: ExtractionRequest) -> ExtractionResult:
        normalized_text = request.text.casefold().strip().rstrip(".")

        if (
            normalized_text
            == "hoy he estudiado 3 horas, he estado concentrado un 8/10 y he hecho 25 ejercicios de álgebra"
        ):
            known_metric_keys = {
                metric.key for metric in request.tracker.known_metrics
            }
            new_metrics = []

            if "study_duration" not in known_metric_keys:
                new_metrics.append(
                    NewMetricProposal(
                        key="study_duration",
                        display_name="Tiempo de estudio",
                        description="Tiempo dedicado a estudiar.",
                        data_type="number",
                        preferred_unit="hours",
                        aggregation="sum",
                    )
                )

            if "concentration" not in known_metric_keys:
                new_metrics.append(
                    NewMetricProposal(
                        key="concentration",
                        display_name="Concentración",
                        description="Nivel subjetivo de concentración durante el estudio.",
                        data_type="number",
                        preferred_unit="score_1_10",
                        aggregation="average",
                    )
                )

            if "exercises_completed" not in known_metric_keys:
                new_metrics.append(
                    NewMetricProposal(
                        key="exercises_completed",
                        display_name="Ejercicios realizados",
                        description="Número de ejercicios completados.",
                        data_type="number",
                        preferred_unit="count",
                        aggregation="sum",
                    )
                )

            event = LifeEvent(
                activity="study",
                date=request.reference_date,
                observations=[
                    {
                        "metric_key": "study_duration",
                        "value": 3,
                        "unit": "hours",
                    },
                    {
                        "metric_key": "concentration",
                        "value": 8,
                        "unit": "score_1_10",
                    },
                    {
                        "metric_key": "exercises_completed",
                        "value": 25,
                        "unit": "count",
                    },
                ],
            )
            return ExtractionResult(events=[event], new_metrics=new_metrics)

        return ExtractionResult(
            unparsed_text=[request.text],
            warnings=[
                "The demo extractor does not recognize this text yet. "
                "An LLM will replace it in the next phase."
            ],
        )
