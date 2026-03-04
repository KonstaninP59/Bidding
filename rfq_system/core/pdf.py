from io import BytesIO
from django.utils import timezone
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm

from .models import Tender, TenderRound, Offer
from .services import rank_offers

def build_analytics_pdf(tender: Tender) -> bytes:
    """
    Генерация аналитической справки (PDF) по обязательным разделам из ТЗ.
    Источник данных: финальный раунд.
    """
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    def h1(text, y):
        c.setFont("Helvetica-Bold", 14)
        c.drawString(20*mm, y, text)

    def p(text, y):
        c.setFont("Helvetica", 10)
        c.drawString(20*mm, y, text)

    # --- Определяем финальный раунд ---
    rounds = list(TenderRound.objects.filter(tender=tender).order_by("number"))
    final_round = rounds[-1] if rounds else None

    # 1) Титульный лист
    y = height - 30*mm
    h1(f"Аналитическая справка по тендеру № {tender.code}", y)
    y -= 10*mm
    p(f"Дата формирования: {timezone.localtime(timezone.now()).strftime('%d.%m.%Y %H:%M')}", y)
    y -= 6*mm
    p(f"Организатор (ответственный): {tender.created_by.email}", y)

    c.showPage()

    # 2) Паспорт тендера
    y = height - 20*mm
    h1("Паспорт тендера", y); y -= 10*mm
    p(f"Предмет закупки: {tender.title}", y); y -= 6*mm
    p(f"Валюта: {tender.currency}", y); y -= 6*mm
    p(f"Структура: {'с лотами' if tender.with_lots else 'без лотов'}", y); y -= 6*mm

    invited = tender.invitations.count()
    participants = Offer.objects.filter(tender=tender, round=final_round).count() if final_round else 0
    p(f"Приглашённых: {invited}; Предложений (финальный раунд): {participants}", y); y -= 6*mm

    c.showPage()

    # 3) Раунды и динамика
    y = height - 20*mm
    h1("Раунды и динамика", y); y -= 10*mm
    if not rounds:
        p("Раунды отсутствуют.", y)
    else:
        for rnd in rounds:
            offers_cnt = Offer.objects.filter(round=rnd).count()
            p(
                f"Раунд {rnd.number}: {rnd.start_at.strftime('%d.%m.%Y %H:%M')} — "
                f"{rnd.deadline_at.strftime('%d.%m.%Y %H:%M')}; "
                f"предложений: {offers_cnt}",
                y
            )
            y -= 6*mm
            if y < 20*mm:
                c.showPage()
                y = height - 20*mm

    c.showPage()

    # 4) Сводная таблица участников (финальный раунд)
    y = height - 20*mm
    h1("Сводная таблица участников (финальный раунд)", y); y -= 10*mm

    if not final_round:
        p("Финальный раунд отсутствует.", y)
        c.showPage()
    else:
        ranked = rank_offers(tender, final_round)
        p("Поставщик | Итоговая цена | Срок | Гарантия | Оплата | Итоговый балл | Статус", y); y -= 6*mm
        c.setFont("Helvetica", 9)
        for offer, Si, rank, disq, reason in ranked:
            status = "Дисквалифицирован" if disq else "Допущен"
            line = (
                f"{offer.supplier.company_name} | {offer.total_price():.2f} | "
                f"{offer.delivery_days or '-'} | {offer.warranty_months or '-'} | "
                f"{offer.payment_terms or '-'} | {Si:.2f} | {status}"
            )
            c.drawString(20*mm, y, line[:120])
            y -= 5*mm
            if disq and reason:
                c.setFont("Helvetica-Oblique", 8)
                c.drawString(22*mm, y, f"Причина: {reason}"[:120])
                y -= 5*mm
                c.setFont("Helvetica", 9)

            if y < 20*mm:
                c.showPage()
                y = height - 20*mm

        c.showPage()

    # 5) Отклонения и риски
    y = height - 20*mm
    h1("Отклонения и риски", y); y -= 10*mm
    if final_round:
        for offer in Offer.objects.filter(tender=tender, round=final_round).select_related("supplier"):
            if offer.deviations.strip():
                p(f"{offer.supplier.company_name}: {offer.deviations[:200]}", y)
                y -= 6*mm
                if y < 20*mm:
                    c.showPage()
                    y = height - 20*mm
    else:
        p("Нет данных.", y)
    c.showPage()

    # 6) Рекомендация и решение
    y = height - 20*mm
    h1("Рекомендация и решение", y); y -= 10*mm

    if final_round:
        ranked = rank_offers(tender, final_round)
        recommended = next((r for r in ranked if not r[3]), None)  # первый недисквалифицированный
        if recommended:
            offer, Si, rank, disq, reason = recommended
            p(f"Рекомендованный победитель (по Si): {offer.supplier.company_name} (Si={Si:.2f})", y); y -= 6*mm
        else:
            p("Рекомендованный победитель: отсутствует (все дисквалифицированы).", y); y -= 6*mm

    if tender.winner_supplier:
        p(f"Выбранный победитель (фактический): {tender.winner_supplier.company_name}", y); y -= 6*mm
        p(f"Обоснование: {tender.winner_reason or '—'}", y); y -= 6*mm
    else:
        p("Выбранный победитель: не назначен.", y); y -= 6*mm

    c.showPage()

    # 7) Приложения
    y = height - 20*mm
    h1("Приложения", y); y -= 10*mm
    if final_round:
        for offer in Offer.objects.filter(tender=tender, round=final_round):
            for att in offer.attachments.all():
                p(f"{offer.supplier.company_name}: {att.title} ({att.uploaded_at.strftime('%d.%m.%Y %H:%M')})", y)
                y -= 6*mm
                if y < 20*mm:
                    c.showPage()
                    y = height - 20*mm
    else:
        p("Нет данных.", y)

    c.save()
    return buf.getvalue()
