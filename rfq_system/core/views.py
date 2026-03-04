from django.db import transaction
from django.db.models import Q

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import HttpResponse, HttpResponseForbidden
from django.db import transaction
from django.core.cache import cache
from django.conf import settings

from django.contrib.auth.models import User

from .models import (
    UserProfile, UserRole,
    Supplier, SupplierDocument, AccreditationStatus,
    Tender, TenderStatus, TenderFile, Lot, Item,
    Criterion,
    TenderInvitation, InvitationStatus,
    TenderRound, RoundState,
    Offer, OfferLine, OfferStatus, OfferVersion,
    ManualScore,
    QuestionAnswer, QaVisibility,
)
from .forms import (
    RuAuthForm, SupplierRegisterForm,
    SupplierProfileForm, SupplierDocumentForm,
    TenderForm, TenderFileForm, LotForm, ItemForm,
    CriterionForm, RoundCreateForm,
    OfferForm, OfferAttachmentForm,
    ManualScoreForm, QaAskForm, QaAnswerForm
)
from .services import (
    audit, send_templated_email,
    ensure_round_states,
    compute_scores_for_round, rank_offers
)
from .pdf import build_analytics_pdf


# -------- helpers --------

def require_role(user, roles):
    if not user.is_authenticated:
        return False
    prof = getattr(user, "profile", None)
    if not prof:
        return False
    return prof.role in roles and not prof.is_blocked

def role_forbidden(request):
    return HttpResponseForbidden("Доступ запрещён.")

def current_round_for_tender(tender: Tender):
    ensure_round_states()
    return TenderRound.objects.filter(tender=tender, state=RoundState.ACTIVE).order_by("-number").first()

def final_round_for_tender(tender: Tender):
    return TenderRound.objects.filter(tender=tender).order_by("-number").first()

def criteria_ok_for_publish(tender: Tender) -> tuple[bool, str]:
    crit = list(Criterion.objects.filter(tender=tender))
    if not crit:
        return False, "Нельзя опубликовать тендер без критериев оценки."
    total = sum(c.weight_percent for c in crit)
    if total != 100:
        return False, f"Сумма весов критериев должна быть 100%. Сейчас: {total}%."
    return True, ""


# -------- auth --------

def login_view(request):
    if request.method == "POST":
        form = RuAuthForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            # Блокировка
            if hasattr(user, "profile") and user.profile.is_blocked:
                messages.error(request, "Пользователь заблокирован администратором.")
                return redirect("login")
            login(request, user)
            cache.delete(f"login_fail:{request.META.get('REMOTE_ADDR','unknown')}")
            return redirect("dashboard")
        else:
            ip = request.META.get("REMOTE_ADDR", "unknown")
            key = f"login_fail:{ip}"
            cache.set(key, cache.get(key, 0) + 1, 60*60)
            messages.error(request, "Неверный Email или пароль.")
    else:
        form = RuAuthForm(request)
    return render(request, "auth/login.html", {"form": form})

def logout_view(request):
    logout(request)
    return redirect("login")

def register_supplier(request):
    if request.method == "POST":
        form = SupplierRegisterForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"].lower()
            pwd = form.cleaned_data["password1"]
            company = form.cleaned_data["company_name"]

            user = User.objects.create_user(username=email, email=email, password=pwd)
            UserProfile.objects.create(user=user, role=UserRole.SUPPLIER, full_name="")
            Supplier.objects.create(user=user, company_name=company, accreditation_status=AccreditationStatus.DRAFT)
            audit(user, "Регистрация поставщика", obj=None, after={"email": email, "company_name": company})

            messages.success(request, "Регистрация завершена. Войдите в систему.")
            return redirect("login")
    else:
        form = SupplierRegisterForm()
    return render(request, "auth/register_supplier.html", {"form": form})


# -------- dashboard --------

@login_required
def dashboard(request):
    ensure_round_states()
    prof = getattr(request.user, "profile", None)
    if not prof:
        messages.error(request, "Не настроен профиль пользователя. Обратитесь к администратору.")
        return redirect("logout")

    if prof.is_blocked:
        messages.error(request, "Ваш аккаунт заблокирован.")
        return redirect("logout")

    if prof.role == UserRole.ADMIN:
        return render(request, "common/dashboard.html", {"role": "ADMIN"})
    if prof.role == UserRole.CUSTOMER:
        return render(request, "common/dashboard.html", {"role": "CUSTOMER"})
    return render(request, "common/dashboard.html", {"role": "SUPPLIER"})


# -------- admin area --------

@login_required
def admin_users(request):
    if not require_role(request.user, [UserRole.ADMIN]):
        return role_forbidden(request)

    users = User.objects.all().select_related()
    profiles = {p.user_id: p for p in UserProfile.objects.select_related("user")}
    return render(request, "admin_area/users.html", {"users": users, "profiles": profiles})

@login_required
def admin_suppliers(request):
    if not require_role(request.user, [UserRole.ADMIN]):
        return role_forbidden(request)

    qs = Supplier.objects.select_related("user").all().order_by("company_name")
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    if q:
        qs = qs.filter(company_name__icontains=q)
    if status:
        qs = qs.filter(accreditation_status=status)

    return render(request, "admin_area/suppliers.html", {"suppliers": qs, "q": q, "status": status})

@login_required
def admin_supplier_review(request, supplier_id):
    if not require_role(request.user, [UserRole.ADMIN]):
        return role_forbidden(request)

    supplier = get_object_or_404(Supplier, id=supplier_id)
    if request.method == "POST":
        new_status = request.POST.get("accreditation_status")
        comment = request.POST.get("accreditation_comment", "").strip()

        before = {"status": supplier.accreditation_status, "comment": supplier.accreditation_comment}
        supplier.accreditation_status = new_status
        supplier.accreditation_comment = comment
        supplier.save()

        audit(request.user, "Смена статуса аккредитации", obj=supplier, before=before, after={"status": new_status, "comment": comment})

        # Email поставщику
        send_templated_email(
            supplier.user.email,
            "accreditation_result",
            {
                "Компания": supplier.company_name,
                "Статус": supplier.get_accreditation_status_display(),
                "Комментарий": comment or "—",
            }
        )

        messages.success(request, "Статус обновлён, уведомление отправлено.")
        return redirect("admin_supplier_review", supplier_id=supplier.id)

    return render(request, "admin_area/supplier_review.html", {"supplier": supplier, "statuses": AccreditationStatus.choices})

@login_required
def audit_list(request):
    if not require_role(request.user, [UserRole.ADMIN]):
        return role_forbidden(request)
    from .models import AuditLog
    logs = AuditLog.objects.select_related("user").order_by("-at")[:500]
    return render(request, "common/audit_list.html", {"logs": logs})

@login_required
def notifications_list(request):
    if not require_role(request.user, [UserRole.ADMIN]):
        return role_forbidden(request)
    from .models import NotificationLog
    logs = NotificationLog.objects.order_by("-created_at")[:500]
    return render(request, "common/notifications_list.html", {"logs": logs})


# -------- customer --------

@login_required
def customer_tender_list(request):
    if not require_role(request.user, [UserRole.CUSTOMER]):
        return role_forbidden(request)
    tenders = Tender.objects.filter(created_by=request.user).order_by("-created_at")
    return render(request, "customer/tender_list.html", {"tenders": tenders})

@login_required
def customer_tender_create(request):
    if not require_role(request.user, [UserRole.CUSTOMER]):
        return role_forbidden(request)

    if request.method == "POST":
        form = TenderForm(request.POST)
        if form.is_valid():
            tender = form.save(commit=False)
            tender.created_by = request.user
            tender.status = TenderStatus.DRAFT
            tender.save()
            audit(request.user, "Создание тендера", obj=tender, after={"code": tender.code, "title": tender.title})
            return redirect("customer_tender_detail", tender_id=tender.id)
    else:
        form = TenderForm()
    return render(request, "customer/tender_create.html", {"form": form})

@login_required
def customer_tender_detail(request, tender_id):
    if not require_role(request.user, [UserRole.CUSTOMER]):
        return role_forbidden(request)

    tender = get_object_or_404(Tender, id=tender_id, created_by=request.user)

    # загрузка файла тендера
    if request.method == "POST" and "upload_tender_file" in request.POST:
        ff = TenderFileForm(request.POST, request.FILES)
        if ff.is_valid():
            f = ff.save(commit=False)
            f.tender = tender
            f.save()
            audit(request.user, "Загрузка файла тендера", obj=tender, after={"file": f.title})
            messages.success(request, "Файл добавлен.")
            return redirect("customer_tender_detail", tender_id=tender.id)
    else:
        ff = TenderFileForm()

    ok_publish, msg = criteria_ok_for_publish(tender)
    return render(request, "customer/tender_detail.html", {
        "tender": tender,
        "file_form": ff,
        "ok_publish": ok_publish,
        "publish_msg": msg,
    })

@login_required
def customer_tender_lots(request, tender_id):
    if not require_role(request.user, [UserRole.CUSTOMER]):
        return role_forbidden(request)
    tender = get_object_or_404(Tender, id=tender_id, created_by=request.user)

    if request.method == "POST":
        form = LotForm(request.POST)
        if form.is_valid():
            lot = form.save(commit=False)
            lot.tender = tender
            lot.save()
            audit(request.user, "Добавление лота", obj=tender, after={"lot": lot.title})
            return redirect("customer_tender_lots", tender_id=tender.id)
    else:
        form = LotForm()

    lots = tender.lots.all()
    return render(request, "customer/tender_lots.html", {"tender": tender, "form": form, "lots": lots})

@login_required
def customer_tender_items(request, tender_id):
    if not require_role(request.user, [UserRole.CUSTOMER]):
        return role_forbidden(request)
    tender = get_object_or_404(Tender, id=tender_id, created_by=request.user)

    if request.method == "POST":
        form = ItemForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.tender = tender
            # Если без лотов — не сохраняем lot
            if not tender.with_lots:
                item.lot = None
            item.save()
            audit(request.user, "Добавление позиции", obj=tender, after={"item": item.name})
            return redirect("customer_tender_items", tender_id=tender.id)
    else:
        form = ItemForm()
        if not tender.with_lots:
            form.fields["lot"].required = False

    items = tender.items.select_related("lot").all()
    return render(request, "customer/tender_items.html", {"tender": tender, "form": form, "items": items})

@login_required
def customer_tender_criteria(request, tender_id):
    if not require_role(request.user, [UserRole.CUSTOMER]):
        return role_forbidden(request)
    tender = get_object_or_404(Tender, id=tender_id, created_by=request.user)

    if request.method == "POST":
        form = CriterionForm(request.POST)
        if form.is_valid():
            c = form.save(commit=False)
            c.tender = tender
            # парсим категориальную таблицу
            try:
                c.category_scores = form.parse_category_scores()
            except Exception as e:
                messages.error(request, str(e))
                return redirect("customer_tender_criteria", tender_id=tender.id)
            c.save()
            audit(request.user, "Добавление критерия", obj=tender, after={"criterion": c.title, "weight": c.weight_percent})
            return redirect("customer_tender_criteria", tender_id=tender.id)
    else:
        form = CriterionForm()

    criteria = tender.criteria.all()
    total = sum(x.weight_percent for x in criteria)
    return render(request, "customer/tender_criteria.html", {"tender": tender, "form": form, "criteria": criteria, "total": total})

@login_required
def customer_tender_invite(request, tender_id):
    if not require_role(request.user, [UserRole.CUSTOMER]):
        return role_forbidden(request)
    tender = get_object_or_404(Tender, id=tender_id, created_by=request.user)

    suppliers = Supplier.objects.filter(accreditation_status=AccreditationStatus.ACCREDITED).order_by("company_name")
    invited_ids = set(tender.invitations.values_list("supplier_id", flat=True))

    if request.method == "POST":
        supplier_id = int(request.POST.get("supplier_id"))
        supplier = get_object_or_404(Supplier, id=supplier_id)

        # без дублей
        if TenderInvitation.objects.filter(tender=tender, supplier=supplier).exists():
            messages.info(request, "Этот поставщик уже приглашён.")
            return redirect("customer_tender_invite", tender_id=tender.id)

        expires = timezone.now() + timezone.timedelta(hours=settings.INVITE_TOKEN_TTL_HOURS)
        inv = TenderInvitation.objects.create(
            tender=tender,
            supplier=supplier,
            expires_at=expires,
            attempts_left=settings.INVITE_MAX_ATTEMPTS,
            created_by=request.user,
        )
        audit(request.user, "Приглашение поставщика", obj=tender, after={"supplier": supplier.company_name})

        # Email
        link = request.build_absolute_uri(f"/i/{inv.token}/")
        send_templated_email(
            supplier.user.email,
            "invite_supplier",
            {
                "НомерТендера": tender.code,
                "Название": tender.title,
                "Дедлайн": "будет указан после публикации",
                "Ссылка": link,
                "КонтактФИО": request.user.profile.full_name or request.user.email,
                "КонтактEmail": request.user.email,
                "КомпанияЗаказчика": "Организация заказчика",
            }
        )

        messages.success(request, "Приглашение создано и отправлено.")
        return redirect("customer_tender_invite", tender_id=tender.id)

    invitations = tender.invitations.select_related("supplier", "supplier__user").order_by("-created_at")
    return render(request, "customer/tender_invite.html", {
        "tender": tender,
        "suppliers": suppliers,
        "invited_ids": invited_ids,
        "invitations": invitations
    })

@login_required
def customer_tender_publish(request, tender_id):
    if not require_role(request.user, [UserRole.CUSTOMER]):
        return role_forbidden(request)
    tender = get_object_or_404(Tender, id=tender_id, created_by=request.user)

    ok, msg = criteria_ok_for_publish(tender)
    if not ok:
        messages.error(request, msg)
        return redirect("customer_tender_detail", tender_id=tender.id)

    if request.method == "POST":
        # создаём раунд 1
        start_at = timezone.now()
        deadline_str = request.POST.get("deadline_at")
        if not deadline_str:
            messages.error(request, "Укажите дедлайн.")
            return redirect("customer_tender_detail", tender_id=tender.id)

        # datetime-local приходит как "YYYY-MM-DDTHH:MM"
        deadline_at = timezone.datetime.fromisoformat(deadline_str)
        deadline_at = timezone.make_aware(deadline_at)

        rnd1, created = TenderRound.objects.get_or_create(
            tender=tender,
            number=1,
            defaults={"start_at": start_at, "deadline_at": deadline_at, "state": RoundState.ACTIVE},
        )
        if not created:
            rnd1.start_at = start_at
            rnd1.deadline_at = deadline_at
            rnd1.state = RoundState.ACTIVE
            rnd1.save()

        # допускаем всех приглашённых в раунд 1
        allowed = [inv.supplier for inv in tender.invitations.select_related("supplier")]
        rnd1.allowed_suppliers.set(allowed)

        tender.status = TenderStatus.PUBLISHED
        tender.save(update_fields=["status"])

        audit(request.user, "Публикация тендера и запуск раунда 1", obj=tender, after={"deadline": deadline_at.isoformat()})

        # уведомляем поставщиков о старте и дедлайне
        for inv in tender.invitations.select_related("supplier__user"):
            link = request.build_absolute_uri(f"/i/{inv.token}/")
            send_templated_email(
                inv.supplier.user.email,
                "round_started",
                {
                    "НомерТендера": tender.code,
                    "Название": tender.title,
                    "Дедлайн": deadline_at.strftime("%d.%m.%Y %H:%M"),
                    "Ссылка": link,
                }
            )

        messages.success(request, "Тендер опубликован, раунд 1 запущен.")
        return redirect("customer_tender_rounds", tender_id=tender.id)

    return redirect("customer_tender_detail", tender_id=tender.id)

@login_required
def customer_tender_rounds(request, tender_id):
    if not require_role(request.user, [UserRole.CUSTOMER]):
        return role_forbidden(request)
    tender = get_object_or_404(Tender, id=tender_id, created_by=request.user)
    ensure_round_states()

    rounds = tender.rounds.all()
    form = RoundCreateForm()

    if request.method == "POST":
        # создаём раунд 2..N
        form = RoundCreateForm(request.POST)
        if form.is_valid():
            next_number = (tender.rounds.count() + 1)
            rnd = form.save(commit=False)
            rnd.tender = tender
            rnd.number = next_number
            rnd.state = RoundState.PLANNED
            rnd.save()

            # допускаем выбранных поставщиков (чекбоксы supplier_<id>)
            allowed = []
            for inv in tender.invitations.select_related("supplier"):
                if request.POST.get(f"supplier_{inv.supplier_id}") == "on":
                    allowed.append(inv.supplier)
            rnd.allowed_suppliers.set(allowed)

            # можно отдельно управлять опцией "поставщик видит своё место" для раунда
            sees_rank = request.POST.get("supplier_sees_rank") == "on"
            tender.supplier_sees_rank = sees_rank
            tender.save(update_fields=["supplier_sees_rank"])

            audit(request.user, f"Создание раунда {rnd.number}", obj=tender, after={"round": rnd.number})

            # уведомление допущенным
            for s in allowed:
                send_templated_email(
                    s.user.email,
                    "round_started",
                    {
                        "НомерТендера": tender.code,
                        "Название": tender.title,
                        "Дедлайн": rnd.deadline_at.strftime("%d.%m.%Y %H:%M"),
                        "Ссылка": request.build_absolute_uri("/supplier/tenders/"),
                    }
                )

            messages.success(request, f"Раунд {rnd.number} создан.")
            return redirect("customer_tender_rounds", tender_id=tender.id)

    invited = tender.invitations.select_related("supplier").all()
    return render(request, "customer/tender_rounds.html", {
        "tender": tender, "rounds": rounds, "form": form, "invited": invited
    })

@login_required
def customer_tender_compare(request, tender_id):
    if not require_role(request.user, [UserRole.CUSTOMER]):
        return role_forbidden(request)
    tender = get_object_or_404(Tender, id=tender_id, created_by=request.user)
    ensure_round_states()

    rnd = final_round_for_tender(tender)
    if not rnd:
        messages.error(request, "Нет раундов.")
        return redirect("customer_tender_detail", tender_id=tender.id)

    # сохранение ручных оценок
    if request.method == "POST":
        offer_id = int(request.POST.get("offer_id"))
        criterion_id = int(request.POST.get("criterion_id"))
        offer = get_object_or_404(Offer, id=offer_id, tender=tender, round=rnd)
        criterion = get_object_or_404(Criterion, id=criterion_id, tender=tender)

        form = ManualScoreForm(request.POST)
        if form.is_valid():
            ManualScore.objects.update_or_create(
                offer=offer, criterion=criterion,
                defaults={"score_0_100": form.cleaned_data["score_0_100"], "comment": form.cleaned_data["comment"]}
            )
            audit(request.user, "Ввод ручной оценки", obj=tender, after={"offer": offer.id, "criterion": criterion.title})
            messages.success(request, "Оценка сохранена.")
        return redirect("customer_tender_compare", tender_id=tender.id)

    ranked = rank_offers(tender, rnd)
    criteria = list(tender.criteria.all())

    # таблица значений
    scores = compute_scores_for_round(tender, rnd)

    # формы ручных оценок
    manual_form = ManualScoreForm()

    return render(request, "customer/tender_compare.html", {
        "tender": tender, "rnd": rnd,
        "criteria": criteria,
        "ranked": ranked,
        "scores": scores,
        "manual_form": manual_form,
    })

@login_required
def customer_tender_close(request, tender_id):
    if not require_role(request.user, [UserRole.CUSTOMER]):
        return role_forbidden(request)
    tender = get_object_or_404(Tender, id=tender_id, created_by=request.user)
    rnd = final_round_for_tender(tender)

    if request.method == "POST":
        winner_id = request.POST.get("winner_supplier_id")
        reason = request.POST.get("winner_reason", "").strip()
        if not winner_id:
            messages.error(request, "Выберите победителя.")
            return redirect("customer_tender_close", tender_id=tender.id)
        if not reason:
            messages.error(request, "Обоснование выбора обязательно.")
            return redirect("customer_tender_close", tender_id=tender.id)

        supplier = get_object_or_404(Supplier, id=int(winner_id))
        tender.winner_supplier = supplier
        tender.winner_reason = reason
        tender.status = TenderStatus.CLOSED
        tender.save()

        audit(request.user, "Закрытие тендера и выбор победителя", obj=tender, after={"winner": supplier.company_name})

        # Уведомляем участников (без раскрытия данных конкурентов)
        if rnd:
            for offer in Offer.objects.filter(tender=tender, round=rnd).select_related("supplier__user"):
                is_winner = (offer.supplier_id == supplier.id)
                send_templated_email(
                    offer.supplier.user.email,
                    "tender_result",
                    {
                        "НомерТендера": tender.code,
                        "Название": tender.title,
                        "Результат": "Вы победили" if is_winner else "Победитель выбран",
                    }
                )

        messages.success(request, "Тендер закрыт.")
        return redirect("customer_tender_detail", tender_id=tender.id)

    # список поставщиков финального раунда (не обязательно допущенные — для простоты)
    suppliers = []
    if rnd:
        suppliers = [o.supplier for o in Offer.objects.filter(tender=tender, round=rnd).select_related("supplier")]

    ranked = rank_offers(tender, rnd) if rnd else []
    return render(request, "customer/tender_close.html", {"tender": tender, "suppliers": suppliers, "ranked": ranked})

@login_required
def customer_tender_pdf(request, tender_id):
    if not require_role(request.user, [UserRole.CUSTOMER]):
        return role_forbidden(request)
    tender = get_object_or_404(Tender, id=tender_id, created_by=request.user)
    pdf_bytes = build_analytics_pdf(tender)
    audit(request.user, "Формирование аналитической справки PDF", obj=tender)
    resp = HttpResponse(pdf_bytes, content_type="application/pdf")
    resp["Content-Disposition"] = f'inline; filename="analytics_{tender.code}.pdf"'
    return resp


# -------- supplier --------

@login_required
def supplier_profile(request):
    if not require_role(request.user, [UserRole.SUPPLIER]):
        return role_forbidden(request)

    supplier = get_object_or_404(Supplier, user=request.user)

    if request.method == "POST" and "save_profile" in request.POST:
        form = SupplierProfileForm(request.POST, instance=supplier)
        if form.is_valid():
            before = {"status": supplier.accreditation_status}
            form.save()
            audit(request.user, "Обновление профиля поставщика", obj=supplier, before=before, after={"status": supplier.accreditation_status})
            messages.success(request, "Профиль сохранён.")
            return redirect("supplier_profile")
    else:
        form = SupplierProfileForm(instance=supplier)

    if request.method == "POST" and "upload_doc" in request.POST:
        dform = SupplierDocumentForm(request.POST, request.FILES)
        if dform.is_valid():
            doc = dform.save(commit=False)
            doc.supplier = supplier
            doc.save()
            audit(request.user, "Загрузка документа аккредитации", obj=supplier, after={"doc_type": doc.doc_type})
            messages.success(request, "Документ загружен.")
            return redirect("supplier_profile")
    else:
        dform = SupplierDocumentForm()

    return render(request, "supplier/supplier_profile.html", {"supplier": supplier, "form": form, "dform": dform})

@login_required
def supplier_tenders(request):
    if not require_role(request.user, [UserRole.SUPPLIER]):
        return role_forbidden(request)

    supplier = get_object_or_404(Supplier, user=request.user)
    ensure_round_states()

    # список тендеров, куда приглашён
    invitations = TenderInvitation.objects.filter(supplier=supplier).select_related("tender").order_by("-created_at")
    tenders = [inv.tender for inv in invitations]
    return render(request, "supplier/supplier_tenders.html", {"tenders": tenders, "invitations": invitations})

@login_required
def supplier_tender_detail(request, tender_id):
    if not require_role(request.user, [UserRole.SUPPLIER]):
        return role_forbidden(request)
    supplier = get_object_or_404(Supplier, user=request.user)
    tender = get_object_or_404(Tender, id=tender_id)

    # проверим, что приглашён
    if not TenderInvitation.objects.filter(tender=tender, supplier=supplier).exists():
        return role_forbidden(request)

    ensure_round_states()
    active_round = current_round_for_tender(tender)
    final_round = final_round_for_tender(tender)

    # если включено "видеть место" и тендер уже на оценке/закрыт — показываем место по финальному раунду
    rank_info = None
    if tender.supplier_sees_rank and final_round:
        ranked = rank_offers(tender, final_round)
        # находим своё предложение
        my = next((r for r in ranked if r[0].supplier_id == supplier.id), None)
        if my:
            offer, Si, rank, disq, reason = my
            participants = len([r for r in ranked if not r[3]])
            rank_info = {
                "rank": rank,
                "participants": participants,
                "Si": Si,
                "disq": disq,
            }

    return render(request, "supplier/supplier_tender_detail.html", {
        "tender": tender,
        "supplier": supplier,
        "active_round": active_round,
        "final_round": final_round,
        "rank_info": rank_info,
    })

@login_required
def supplier_offer_edit(request, tender_id, round_id):
    if not require_role(request.user, [UserRole.SUPPLIER]):
        return role_forbidden(request)

    supplier = get_object_or_404(Supplier, user=request.user)
    tender = get_object_or_404(Tender, id=tender_id)
    rnd = get_object_or_404(TenderRound, id=round_id, tender=tender)

    if not rnd.allowed_suppliers.filter(id=supplier.id).exists():
        return role_forbidden(request)

    ensure_round_states()

    offer, _ = Offer.objects.get_or_create(tender=tender, round=rnd, supplier=supplier)

    # если дедлайн прошёл — запрет редактирования
    if not rnd.is_editable_now() or offer.status == OfferStatus.LOCKED:
        messages.error(request, "Редактирование недоступно: раунд завершён или предложение зафиксировано.")
        return redirect("supplier_tender_detail", tender_id=tender.id)

    # создаём линии по позициям, если их нет
    if offer.lines.count() == 0:
        with transaction.atomic():
            for item in tender.items.all():
                OfferLine.objects.create(offer=offer, item=item, qty=item.qty)

    if request.method == "POST" and "save_offer" in request.POST:
        form = OfferForm(request.POST, instance=offer)
        if form.is_valid():
            form.save()
            # цены по позициям
            for line in offer.lines.select_related("item"):
                key = f"price_{line.id}"
                val = request.POST.get(key, "").strip()
                if val == "":
                    line.price = None
                else:
                    try:
                        line.price = float(val)
                    except:
                        line.price = None
                line.save(update_fields=["price"])
            audit(request.user, "Сохранение черновика предложения", obj=offer, after={"offer_id": offer.id})
            messages.success(request, "Черновик сохранён.")
            return redirect("supplier_offer_edit", tender_id=tender.id, round_id=rnd.id)
    else:
        form = OfferForm(instance=offer)

    return render(request, "supplier/offer_edit.html", {"tender": tender, "rnd": rnd, "offer": offer, "form": form})

# -------- Invitation hybrid “C” --------

def invitation_landing(request, token):
    ensure_round_states()
    inv = get_object_or_404(TenderInvitation, token=token)

    if not inv.is_valid():
        inv.status = InvitationStatus.EXPIRED
        inv.save(update_fields=["status"])
        return render(request, "supplier/invitation_landing.html", {"inv": inv, "expired": True})

    # уменьшаем попытки
    inv.attempts_left -= 1
    if inv.status == InvitationStatus.SENT:
        inv.status = InvitationStatus.OPENED
        inv.opened_at = timezone.now()
    inv.save(update_fields=["attempts_left", "status", "opened_at"])

    tender = inv.tender
    rnd = current_round_for_tender(tender)

    return render(request, "supplier/invitation_landing.html", {
        "inv": inv, "tender": tender, "rnd": rnd, "expired": False
    })

def invitation_offer(request, token):
    ensure_round_states()
    inv = get_object_or_404(TenderInvitation, token=token)

    if not inv.is_valid():
        return redirect("invitation_landing", token=token)

    tender = inv.tender
    supplier = inv.supplier
    rnd = current_round_for_tender(tender)
    if not rnd:
        messages.error(request, "Сейчас нет активного раунда.")
        return redirect("invitation_landing", token=token)

    if not rnd.allowed_suppliers.filter(id=supplier.id).exists():
        messages.error(request, "Вы не допущены к текущему раунду.")
        return redirect("invitation_landing", token=token)

    offer, _ = Offer.objects.get_or_create(tender=tender, round=rnd, supplier=supplier)

    # если дедлайн прошёл — нельзя
    if not rnd.is_editable_now():
        messages.error(request, "Дедлайн уже прошёл.")
        return redirect("invitation_landing", token=token)

    # создаём линии
    if offer.lines.count() == 0:
        for item in tender.items.all():
            OfferLine.objects.create(offer=offer, item=item, qty=item.qty)

    if request.method == "POST" and "submit_offer" in request.POST:
        # сохраняем поля
        form = OfferForm(request.POST, instance=offer)
        if form.is_valid():
            form.save()

            for line in offer.lines.all():
                key = f"price_{line.id}"
                val = request.POST.get(key, "").strip()
                line.price = float(val) if val else None
                line.save(update_fields=["price"])

            # статус "Отправлено"
            offer.status = OfferStatus.SUBMITTED
            offer.submitted_at = timezone.now()
            offer.save(update_fields=["status", "submitted_at"])

            # версия
            snapshot = {
                "offer": {
                    "delivery_days": offer.delivery_days,
                    "payment_terms": offer.payment_terms,
                    "warranty_months": offer.warranty_months,
                    "validity_days": offer.validity_days,
                    "deviations": offer.deviations,
                    "comment": offer.comment,
                    "total_price": offer.total_price(),
                },
                "lines": [
                    {"item": l.item.name, "qty": float(l.qty), "price": float(l.price) if l.price is not None else None}
                    for l in offer.lines.select_related("item")
                ],
            }
            OfferVersion.objects.create(offer=offer, snapshot_json=snapshot)
            audit(None, "Подача предложения по персональной ссылке", obj=offer, after={"tender": tender.code, "supplier": supplier.company_name})

            inv.status = InvitationStatus.USED
            inv.save(update_fields=["status"])

            # После первой отправки — предлагаем создать кабинет
            return redirect("invitation_create_account", token=token)

    form = OfferForm(instance=offer)
    return render(request, "supplier/offer_edit.html", {
        "tender": tender, "rnd": rnd, "offer": offer, "form": form,
        "invitation_mode": True, "token": token
    })

def invitation_create_account(request, token):
    inv = get_object_or_404(TenderInvitation, token=token)
    supplier = inv.supplier
    user = supplier.user

    # Если пароль уже есть и пользователь может логиниться — просто уводим в логин
    if user.has_usable_password():
        messages.info(request, "Кабинет уже создан. Войдите в систему.")
        return redirect("login")

    if request.method == "POST":
        pwd1 = request.POST.get("password1")
        pwd2 = request.POST.get("password2")
        if not pwd1 or len(pwd1) < 10:
            messages.error(request, "Пароль должен быть не короче 10 символов.")
            return redirect("invitation_create_account", token=token)
        if pwd1 != pwd2:
            messages.error(request, "Пароли не совпадают.")
            return redirect("invitation_create_account", token=token)

        user.set_password(pwd1)
        user.save(update_fields=["password"])
        audit(user, "Создание кабинета после первой отправки", obj=supplier)

        messages.success(request, "Кабинет создан. Теперь вы можете входить по Email и паролю.")
        return redirect("login")

    return render(request, "supplier/create_account_after_submit.html", {"supplier": supplier})


# -------- Q&A (поставщик) --------

@login_required
def supplier_qa(request, tender_id):
    if not require_role(request.user, [UserRole.SUPPLIER]):
        return role_forbidden(request)
    supplier = get_object_or_404(Supplier, user=request.user)
    tender = get_object_or_404(Tender, id=tender_id)

    if not TenderInvitation.objects.filter(tender=tender, supplier=supplier).exists():
        return role_forbidden(request)

    if request.method == "POST":
        form = QaAskForm(request.POST)
        if form.is_valid():
            qa = form.save(commit=False)
            qa.tender = tender
            qa.supplier = supplier
            qa.save()
            audit(request.user, "Вопрос в Q&A", obj=tender, after={"qa_id": qa.id})
            messages.success(request, "Вопрос отправлен.")
            # уведомим заказчика
            send_templated_email(
                tender.created_by.email,
                "qa_new_question",
                {"НомерТендера": tender.code, "Название": tender.title}
            )
            return redirect("supplier_qa", tender_id=tender.id)
    else:
        form = QaAskForm()

    # поставщик видит:
    # - свои вопросы
    # - общие вопросы (visibility=ALL)
    qa_list = QuestionAnswer.objects.filter(tender=tender).filter(
        Q(visibility=QaVisibility.ALL) | Q(supplier=supplier)
    ).order_by("-created_at")

    return render(request, "supplier/qa_list.html", {"tender": tender, "form": form, "qa_list": qa_list})
