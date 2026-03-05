from typing import List, Dict
from app.models import Proposal, TenderCriterion, CriterionType


def normalize_value(value: float, criterion_type: str, all_values: List[float]) -> float:
    """
    Нормализует значение критерия в диапазон [0,100].
    Для минимизации: 100 * (min / x)
    Для максимизации: 100 * (x / max)
    """
    if not all_values:
        return 0
    if criterion_type == CriterionType.NUMERIC_MIN:
        min_val = min(all_values)
        if min_val == 0:
            return 100 if value == 0 else 0  # защита от деления на ноль
        return 100 * (min_val / value) if value != 0 else 0
    elif criterion_type == CriterionType.NUMERIC_MAX:
        max_val = max(all_values)
        if max_val == 0:
            return 0
        return 100 * (value / max_val)
    else:
        # Для категориальных и ручных балл уже должен быть задан
        return value


def calculate_final_score(proposal: Proposal, criteria: List[TenderCriterion], all_proposals: List[Proposal]) -> float:
    """
    Рассчитывает итоговый балл предложения.
    Собирает все значения по каждому критерию, нормализует, взвешивает.
    """
    # Собираем значения по критериям для всех предложений (для нормализации)
    criterion_values: Dict[int, List[float]] = {}
    for p in all_proposals:
        for val in p.values:
            if val.value_numeric is not None:
                criterion_values.setdefault(val.criterion_id, []).append(val.value_numeric)

    total = 0.0
    for val in proposal.values:
        crit = next((c for c in criteria if c.id == val.criterion_id), None)
        if not crit:
            continue
        if crit.criterion_type in (CriterionType.NUMERIC_MIN, CriterionType.NUMERIC_MAX):
            norm = normalize_value(val.value_numeric, crit.criterion_type, criterion_values.get(crit.id, []))
        else:
            # Для ручных и категориальных ожидаем уже готовый балл в value_numeric
            norm = val.value_numeric or 0
        weighted = norm * (crit.weight / 100.0)
        total += weighted
        val.score_normalized = norm
    return total
