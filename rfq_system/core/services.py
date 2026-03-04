from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction

from .models import (
    AuditLog, NotificationLog, EmailTemplate,
    Tender, TenderRound, RoundState,
    Offer, OfferStatus,
    Criterion, CriterionType, CriterionSource,
    ManualScore
)

def audit(user, action, obj=None, before=None, after=None):
    AuditLog.objects.create(
        user=user if user and getattr(user, "is_authenticated", False) else None,
        action=action,
        object_type=obj.__class__.__name__ if obj else "",
        object_id=str(getattr(obj, "id", "")) if obj else "",
        before=before or {},
        after=after or {},
    )

def render_template_text(template: EmailTemplate, context: dict) -> tuple[str, str]:
    """
    Очень простой рендер: подстановка {Ключ}.
    """
    subject = template.subject
    body = template.body
    for k, v in context.items():
        subject = subject.replace("{" + k + "}", str(v))
        body = body.replace("{" + k + "}", str(v))
    return subject, body

def send_templated_email(to_email: str, template_slug: str, context: dict):
    """
    Email-канал по ТЗ — только Email.
    Логируем каждую попытку.
    """
    try:
        tpl = EmailTemplate.objects.get(slug=template_slug)
        subject, body = render_template_text(tpl, context)
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [to_email], fail_silently=False)
        NotificationLog.objects.create(to_email=to_email, template_slug=template_slug, subject=subject, status="OK")
    except Exception as e:
        NotificationLog.objects.create(to_email=to_email, template_slug=template_slug, subject="", status="FAIL", error=str(e))

def ensure_round_states():
    """
    Обновляем состояния раундов по времени (простая "автоматизация" без очередей).
    Можно запускать командой close_rounds (см. management command) по cron.
    """
    now = timezone.now()

    # Активируем запланированные
    for rnd in TenderRound.objects.filter(state=RoundState.PLANNED, start_at__lte=now, deadline_at__gt=now):
        rnd.state = RoundState.ACTIVE
        rnd.save(update_fields=["state"])

    # Завершаем активные
    for rnd in TenderRound.objects.filter(state=RoundState.ACTIVE, deadline_at__lte=now):
        rnd.state = RoundState.FINISHED
        rnd.save(update_fields=["state"])
        lock_offers_by_deadline(rnd)

def lock_offers_by_deadline(rnd: TenderRound):
    """
    По дедлайну фиксируем предложения => LOCKED.
    """
    with transaction.atomic():
        offers = Offer.objects.select_for_update().filter(round=rnd).exclude(status=OfferStatus.LOCKED)
        for offer in offers:
            # если не отправлено — считаем черновик тоже фиксируем как "Зафиксировано"
            offer.status = OfferStatus.LOCKED
            offer.locked_at = timezone.now()
            offer.save(update_fields=["status", "locked_at"])

def criterion_value(offer: Offer, criterion: Criterion):
    """
    Достаём x_ik.
    """
    src = criterion.source
    if src == CriterionSource.PRICE_TOTAL:
        return offer.total_price()
    if src == CriterionSource.DELIVERY_DAYS:
        return offer.delivery_days
    if src == CriterionSource.WARRANTY_MONTHS:
        return offer.warranty_months
    if src == CriterionSource.VALIDITY_DAYS:
        return offer.validity_days
    if src == CriterionSource.PAYMENT_TERMS:
        return (offer.payment_terms or "").strip()
    if src == CriterionSource.MANUAL:
        ms = ManualScore.objects.filter(offer=offer, criterion=criterion).first()
        return ms.score_0_100 if ms else None
    return None

def mandatory_passed(offer: Offer, criterion: Criterion) -> tuple[bool, str]:
    """
    Простая логика pass/fail:
    - для числовых: значение должно быть задано и > 0
    - для price_total: total_price > 0
    - для категориального: строка должна быть задана и быть в таблице category_scores
    - для ручного: должна быть выставлена ручная оценка
    """
    val = criterion_value(offer, criterion)

    if criterion.source == CriterionSource.PRICE_TOTAL:
        ok = (val is not None) and (val > 0)
        return ok, "Не указана цена (или цена равна 0)."

    if criterion.ctype in [CriterionType.NUMERIC_MIN, CriterionType.NUMERIC_MAX]:
        ok = (val is not None) and (float(val) > 0)
        return ok, f"Не заполнено обязательное числовое поле: {criterion.title}."

    if criterion.ctype == CriterionType.CATEGORICAL:
        s = (val or "").strip()
        ok = bool(s) and (s in (criterion.category_scores or {}))
        return ok, f"Условие '{s}' не найдено в таблице баллов для критерия: {criterion.title}."

    if criterion.ctype == CriterionType.MANUAL:
        ok = val is not None
        return ok, f"Не выставлена ручная оценка по критерию: {criterion.title}."

    return True, ""

def compute_scores_for_round(tender: Tender, rnd: TenderRound):
    """
    Считаем sik и Si для предложений финального раунда (или любого выбранного).
    Возвращаем структуру:
    {
      offer_id: {
        "disqualified": bool,
        "reason": str,
        "by_criterion": {criterion_id: sik},
        "Si": итог 0..100
      },
      ...
    }
    Формулы из ТЗ (нормировка 0..100).
    """
    # Берём только зафиксированные/отправленные (для сравнения можно все, но ранжируем финальные)
    offers = list(Offer.objects.filter(tender=tender, round=rnd).select_related("supplier"))

    criteria = list(Criterion.objects.filter(tender=tender))
    result = {}

    # Сначала pass/fail
    for offer in offers:
        disq = False
        reasons = []
        for c in criteria:
            if c.mandatory:
                ok, reason = mandatory_passed(offer, c)
                if not ok:
                    disq = True
                    reasons.append(reason)
        result[offer.id] = {
            "disqualified": disq,
            "reason": "; ".join([r for r in reasons if r]),
            "by_criterion": {},
            "Si": 0.0,
        }

    # Подготовим min/max по каждому числовому критерию (только среди НЕ дисквалифицированных)
    numeric_values = {}  # c.id -> list[float]
    for c in criteria:
        if c.ctype in [CriterionType.NUMERIC_MIN, CriterionType.NUMERIC_MAX]:
            vals = []
            for offer in offers:
                if result[offer.id]["disqualified"]:
                    continue
                v = criterion_value(offer, c)
                if v is None:
                    continue
                try:
                    vals.append(float(v))
                except Exception:
                    pass
            numeric_values[c.id] = vals

    # Считаем sik и Si
    for offer in offers:
        if result[offer.id]["disqualified"]:
            # Записываем причину в предложение (для отчёта)
            if result[offer.id]["reason"]:
                Offer.objects.filter(id=offer.id).update(
                    status=OfferStatus.DISQUALIFIED,
                    disqualification_reason=result[offer.id]["reason"]
                )
            continue

        Si = 0.0
        for c in criteria:
            val = criterion_value(offer, c)
            sik = 0.0

            if c.ctype == CriterionType.NUMERIC_MIN:
                vals = numeric_values.get(c.id, [])
                if vals and val is not None:
                    mn = min(vals)
                    x = float(val)
                    # sik = 100 * min / x
                    if x <= 0:
                        sik = 0.0
                    elif mn == 0 and x == 0:
                        sik = 100.0
                    else:
                        sik = 100.0 * (mn / x)

            elif c.ctype == CriterionType.NUMERIC_MAX:
                vals = numeric_values.get(c.id, [])
                if vals and val is not None:
                    mx = max(vals)
                    x = float(val)
                    # sik = 100 * x / max
                    if mx <= 0:
                        sik = 0.0
                    else:
                        sik = 100.0 * (x / mx)

            elif c.ctype == CriterionType.CATEGORICAL:
                s = (val or "").strip()
                sik = float((c.category_scores or {}).get(s, 0))

            elif c.ctype == CriterionType.MANUAL:
                sik = float(val) if val is not None else 0.0

            # ограничим 0..100
            sik = max(0.0, min(100.0, sik))
            result[offer.id]["by_criterion"][c.id] = sik

            # Итог: wk% * sik (wk в процентах)
            Si += (c.weight_percent / 100.0) * sik

        result[offer.id]["Si"] = round(Si, 2)

    return result

def rank_offers(tender: Tender, rnd: TenderRound):
    """
    Ранжируем по Si (по ТЗ).
    Возвращаем список: [(offer, Si, rank, disqualified, reason), ...]
    """
    scores = compute_scores_for_round(tender, rnd)
    offers = list(Offer.objects.filter(tender=tender, round=rnd).select_related("supplier"))

    rows = []
    for offer in offers:
        s = scores.get(offer.id, {})
        rows.append((offer, s.get("Si", 0.0), s.get("disqualified", False), s.get("reason", "")))

    # Дисквалифицированные внизу
    rows.sort(key=lambda x: (x[2], -x[1]))  # сначала False, потом True; Si по убыванию

    ranked = []
    rank = 0
    for offer, Si, disq, reason in rows:
        if disq:
            ranked.append((offer, Si, None, disq, reason))
        else:
            rank += 1
            ranked.append((offer, Si, rank, disq, reason))
    return ranked
