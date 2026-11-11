"""Modelo preditivo complementar em scikit-learn para cálculo do Score Técnico de Risco Urbano."""

from functools import lru_cache
from typing import Tuple

import numpy as np
from sklearn.ensemble import RandomForestRegressor

from backend.app.schemas.occurrence_schema import VulnerabilityContext

HIGH_HAZARD_KEYWORDS = (
    "alagamento",
    "inundação",
    "inundacao",
    "desabamento",
    "deslizamento",
    "fios caídos",
    "fio desencapado",
    "choque",
    "cratera",
    "árvore caindo",
    "arvore caindo",
    "enchente",
    "correnteza",
    "bueiro aberto",
)

ACCESSIBILITY_AND_MOBILITY_KEYWORDS = (
    "cadeirante",
    "cadeira de rodas",
    "rampa",
    "calçada",
    "calcada",
    "idoso",
    "cego",
    "deficiência",
    "deficiencia",
    "piso tátil",
    "piso tatil",
    "bloqueada",
    "intransitável",
)

VULNERABILITY_WEIGHT_MAP = {
    VulnerabilityContext.NENHUMA_ESPECIFICA: 0.15,
    VulnerabilityContext.PESSOA_COM_DEFICIENCIA_OU_IDOSO: 0.85,
    VulnerabilityContext.ENTORNO_ESCOLAR_OU_SAUDE: 0.80,
    VulnerabilityContext.AREA_DE_ENCOSTA_OU_MARGEM_CORREGO: 0.95,
}


@lru_cache(maxsize=1)
def _get_trained_urban_risk_regressor() -> RandomForestRegressor:
    """Treina e mantém em memória um modelo RandomForestRegressor calibrado para triagem urbana."""
    # Matriz de treinamento: [hazard_kw, access_kw, rain_norm, vuln_weight, has_photo]
    training_features = np.array(
        [
            [0.0, 0.0, 0.0, 0.15, 0.0],
            [0.0, 0.3, 0.0, 0.15, 1.0],
            [0.2, 0.6, 0.1, 0.85, 1.0],
            [0.5, 0.2, 0.3, 0.80, 0.0],
            [0.8, 0.1, 0.6, 0.80, 1.0],
            [1.0, 0.5, 0.8, 0.95, 1.0],
            [0.9, 0.0, 0.9, 0.95, 0.0],
            [0.3, 0.9, 0.0, 0.85, 1.0],
            [0.1, 0.1, 0.2, 0.15, 0.0],
            [0.7, 0.4, 0.5, 0.85, 1.0],
            [0.4, 0.4, 0.4, 0.50, 0.0],
            [1.0, 1.0, 1.0, 0.95, 1.0],
        ],
        dtype=float,
    )
    training_targets = np.array(
        [18.0, 34.0, 68.0, 64.0, 86.0, 96.0, 94.0, 74.0, 28.0, 82.0, 55.0, 99.0],
        dtype=float,
    )

    regressor = RandomForestRegressor(
        n_estimators=40,
        max_depth=5,
        random_state=42,
    )
    regressor.fit(training_features, training_targets)
    return regressor


def _extract_feature_vector(
    description: str,
    precipitation_mm: float,
    vulnerability_context: VulnerabilityContext,
    has_photo_evidence: bool,
) -> Tuple[float, float, float, float, float]:
    """Extrai o vetor numérico de atributos a partir do relato e da telemetria climática."""
    normalized_text = description.lower()

    hazard_matches = sum(1 for kw in HIGH_HAZARD_KEYWORDS if kw in normalized_text)
    hazard_intensity = min(1.0, hazard_matches / 2.0)

    accessibility_matches = sum(
        1 for kw in ACCESSIBILITY_AND_MOBILITY_KEYWORDS if kw in normalized_text
    )
    accessibility_intensity = min(1.0, accessibility_matches / 2.0)

    precipitation_normalized = min(1.0, max(0.0, precipitation_mm / 20.0))
    vulnerability_weight = VULNERABILITY_WEIGHT_MAP.get(vulnerability_context, 0.2)
    photo_flag = 1.0 if has_photo_evidence else 0.0

    return (
        hazard_intensity,
        accessibility_intensity,
        precipitation_normalized,
        vulnerability_weight,
        photo_flag,
    )


def compute_urban_technical_risk_score(
    description: str,
    precipitation_mm: float,
    vulnerability_context: VulnerabilityContext,
    has_photo_evidence: bool,
) -> float:
    """Executa inferência no modelo scikit-learn para produzir um score técnico de 0 a 100."""
    feature_vector = _extract_feature_vector(
        description=description,
        precipitation_mm=precipitation_mm,
        vulnerability_context=vulnerability_context,
        has_photo_evidence=has_photo_evidence,
    )
    model = _get_trained_urban_risk_regressor()
    predicted_score = float(model.predict(np.array([feature_vector], dtype=float))[0])
    return round(min(99.5, max(5.0, predicted_score)), 1)
