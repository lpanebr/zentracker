from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation


@dataclass(frozen=True)
class MetricSpec:
    name: str

    def validate(self, raw_value: str) -> str:
        raise NotImplementedError


@dataclass(frozen=True)
class WeightMetric(MetricSpec):
    def validate(self, raw_value: str) -> str:
        value = raw_value.strip()
        if not value:
            raise ValueError("peso exige um valor numerico.")

        try:
            Decimal(value)
        except InvalidOperation as exc:
            raise ValueError("peso exige um valor numerico.") from exc

        return value


@dataclass(frozen=True)
class GymMetric(MetricSpec):
    def validate(self, raw_value: str) -> str:
        value = raw_value.strip().lower()
        if value not in {"sim", "nao"}:
            raise ValueError("academia aceita apenas 'sim' ou 'nao'.")
        return value


METRICS: dict[str, MetricSpec] = {
    "peso": WeightMetric(name="peso"),
    "academia": GymMetric(name="academia"),
}


def metric_names() -> list[str]:
    return sorted(METRICS)


def get_metric(metric_name: str) -> MetricSpec:
    try:
        return METRICS[metric_name]
    except KeyError as exc:
        valid = ", ".join(sorted(METRICS))
        raise ValueError(f"metrica desconhecida: {metric_name}. Opcoes: {valid}.") from exc
