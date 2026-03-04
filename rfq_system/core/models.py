from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid

# --- Роли (простая RBAC-модель через профиль пользователя) ---

class UserRole(models.TextChoices):
    ADMIN = "ADMIN", "Админ"
    CUSTOMER = "CUSTOMER", "Заказчик"
    SUPPLIER = "SUPPLIER", "Поставщик"

class UserProfile(models.Model):
    """
    Профиль пользователя: роль + ФИО/телефон/должность и т.д.
    (Делаем максимально просто: используем встроенного User.)
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=20, choices=UserRole.choices, default=UserRole.SUPPLIER)

    full_name = models.CharField("ФИО", max_length=200, blank=True)
    position = models.CharField("Должность", max_length=200, blank=True)
    phone = models.CharField("Телефон", max_length=50, blank=True)

    is_blocked = models.BooleanField("Заблокирован", default=False)

    def __str__(self):
        return f"{self.user.email} ({self.get_role_display()})"


# --- Поставщики и аккредитация ---

class AccreditationStatus(models.TextChoices):
    DRAFT = "DRAFT", "Черновик"
    REVIEW = "REVIEW", "На проверке"
    ACCREDITED = "ACCREDITED", "Аккредитован"
    REJECTED = "REJECTED", "Отказ"
    SUSPENDED = "SUSPENDED", "Приостановлен"

class Supplier(models.Model):
    """
    Карточка поставщика привязана к пользователю-логину.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="supplier")

    company_name = models.CharField("Наименование", max_length=255)
    inn = models.CharField("ИНН", max_length=20, blank=True)
    kpp = models.CharField("КПП", max_length=20, blank=True)
    ogrn = models.CharField("ОГРН", max_length=20, blank=True)

    address = models.CharField("Адрес", max_length=500, blank=True)
    contacts = models.TextField("Контакты", blank=True)

    categories = models.CharField("Категории/теги", max_length=500, blank=True)

    accreditation_status = models.CharField(
        "Статус аккредитации",
        max_length=20,
        choices=AccreditationStatus.choices,
        default=AccreditationStatus.DRAFT,
    )
    accreditation_comment = models.TextField("Комментарий по аккредитации", blank=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.company_name

class SupplierDocument(models.Model):
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name="documents")
    doc_type = models.CharField("Тип документа", max_length=200)
    file = models.FileField(upload_to="supplier_docs/")
    expires_at = models.DateField("Срок действия", null=True, blank=True)
    comment = models.CharField("Комментарий", max_length=500, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)


# --- Тендеры, лоты, позиции, файлы ---

class TenderStatus(models.TextChoices):
    DRAFT = "DRAFT", "Черновик"
    PUBLISHED = "PUBLISHED", "Опубликован"
    EVALUATION = "EVALUATION", "На оценке"
    CLOSED = "CLOSED", "Закрыт"
    CANCELLED = "CANCELLED", "Отменён"

class Tender(models.Model):
    code = models.CharField("Номер/код", max_length=30, unique=True, editable=False)
    title = models.CharField("Название", max_length=255)
    description = models.TextField("Описание", blank=True)

    currency = models.CharField("Валюта", max_length=10, default="RUB")

    with_lots = models.BooleanField("С лотами", default=False)

    allow_alternatives = models.BooleanField("Альтернативы", default=False)
    allow_partial = models.BooleanField("Частичная подача", default=False)
    price_format = models.CharField(
        "Формат цен",
        max_length=20,
        choices=[("PER_ITEM", "По позициям"), ("PER_LOT", "По лоту")],
        default="PER_ITEM",
    )

    supplier_sees_rank = models.BooleanField("Поставщик видит своё место", default=False)

    status = models.CharField(max_length=20, choices=TenderStatus.choices, default=TenderStatus.DRAFT)

    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="tenders_created")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    winner_supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True, related_name="wins")
    winner_reason = models.TextField("Обоснование выбора победителя", blank=True)

    def __str__(self):
        return f"{self.code} — {self.title}"

    def save(self, *args, **kwargs):
        if not self.code:
            # Простой авто-код: RFQ-YYYY-XXXX
            year = timezone.now().year
            last = Tender.objects.filter(code__startswith=f"RFQ-{year}-").count() + 1
            self.code = f"RFQ-{year}-{last:04d}"
        return super().save(*args, **kwargs)

class TenderFile(models.Model):
    tender = models.ForeignKey(Tender, on_delete=models.CASCADE, related_name="files")
    title = models.CharField("Название файла", max_length=255)
    file = models.FileField(upload_to="tender_files/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

class Lot(models.Model):
    tender = models.ForeignKey(Tender, on_delete=models.CASCADE, related_name="lots")
    title = models.CharField("Название лота", max_length=255)
    description = models.TextField("Описание", blank=True)
    place = models.CharField("Место поставки/работ", max_length=255, blank=True)
    terms = models.TextField("Условия", blank=True)

    def __str__(self):
        return self.title

class Item(models.Model):
    tender = models.ForeignKey(Tender, on_delete=models.CASCADE, related_name="items")
    lot = models.ForeignKey(Lot, on_delete=models.SET_NULL, null=True, blank=True, related_name="items")

    name = models.CharField("Наименование", max_length=255)
    qty = models.DecimalField("Количество", max_digits=12, decimal_places=3, validators=[MinValueValidator(0)])
    unit = models.CharField("Ед. изм.", max_length=50, default="шт")
    requirements = models.TextField("Технические требования/комментарии", blank=True)

    def __str__(self):
        return self.name


# --- Раунды, приглашения, предложения ---

class RoundState(models.TextChoices):
    PLANNED = "PLANNED", "Запланирован"
    ACTIVE = "ACTIVE", "Идёт"
    FINISHED = "FINISHED", "Завершён"

class TenderRound(models.Model):
    tender = models.ForeignKey(Tender, on_delete=models.CASCADE, related_name="rounds")
    number = models.PositiveIntegerField("Номер раунда")
    start_at = models.DateTimeField("Начало")
    deadline_at = models.DateTimeField("Дедлайн")
    state = models.CharField(max_length=20, choices=RoundState.choices, default=RoundState.PLANNED)

    allowed_suppliers = models.ManyToManyField(Supplier, blank=True, related_name="allowed_rounds")

    class Meta:
        unique_together = [("tender", "number")]
        ordering = ["number"]

    def __str__(self):
        return f"{self.tender.code} Раунд {self.number}"

    def is_editable_now(self):
        now = timezone.now()
        return self.state == RoundState.ACTIVE and now < self.deadline_at

class InvitationStatus(models.TextChoices):
    SENT = "SENT", "Отправлено"
    OPENED = "OPENED", "Открыто"
    USED = "USED", "Использовано"
    EXPIRED = "EXPIRED", "Истекло"

class TenderInvitation(models.Model):
    tender = models.ForeignKey(Tender, on_delete=models.CASCADE, related_name="invitations")
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name="invitations")

    token = models.CharField(max_length=64, unique=True, editable=False)
    expires_at = models.DateTimeField()
    attempts_left = models.PositiveIntegerField(default=30)
    status = models.CharField(max_length=20, choices=InvitationStatus.choices, default=InvitationStatus.SENT)

    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="invitations_created")
    created_at = models.DateTimeField(auto_now_add=True)
    opened_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = uuid.uuid4().hex + uuid.uuid4().hex  # 64 символа
        super().save(*args, **kwargs)

    def is_valid(self):
        return self.attempts_left > 0 and timezone.now() < self.expires_at

class OfferStatus(models.TextChoices):
    DRAFT = "DRAFT", "Черновик"
    SUBMITTED = "SUBMITTED", "Отправлено"
    LOCKED = "LOCKED", "Зафиксировано"
    DISQUALIFIED = "DISQUALIFIED", "Дисквалифицировано"

class Offer(models.Model):
    tender = models.ForeignKey(Tender, on_delete=models.CASCADE, related_name="offers")
    round = models.ForeignKey(TenderRound, on_delete=models.CASCADE, related_name="offers")
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name="offers")

    status = models.CharField(max_length=20, choices=OfferStatus.choices, default=OfferStatus.DRAFT)

    # Условия
    delivery_days = models.PositiveIntegerField("Срок поставки (дни)", null=True, blank=True)
    payment_terms = models.CharField("Условия оплаты", max_length=200, blank=True)
    warranty_months = models.PositiveIntegerField("Гарантия (мес.)", null=True, blank=True)
    validity_days = models.PositiveIntegerField("Валидность КП (дни)", null=True, blank=True)

    deviations = models.TextField("Отклонения", blank=True)
    comment = models.TextField("Комментарий", blank=True)

    disqualification_reason = models.TextField("Причина дисквалификации", blank=True)

    submitted_at = models.DateTimeField(null=True, blank=True)
    locked_at = models.DateTimeField(null=True, blank=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("tender", "round", "supplier")]

    def total_price(self):
        # Итоговая цена = сумма по позициям
        total = 0
        for line in self.lines.all():
            if line.price is not None:
                total += float(line.price) * float(line.qty)
        return total

class OfferLine(models.Model):
    offer = models.ForeignKey(Offer, on_delete=models.CASCADE, related_name="lines")
    item = models.ForeignKey(Item, on_delete=models.PROTECT)
    qty = models.DecimalField(max_digits=12, decimal_places=3)
    price = models.DecimalField("Цена за единицу", max_digits=14, decimal_places=2, null=True, blank=True)

class OfferAttachment(models.Model):
    offer = models.ForeignKey(Offer, on_delete=models.CASCADE, related_name="attachments")
    title = models.CharField("Название", max_length=255)
    file = models.FileField(upload_to="offer_attachments/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

class OfferVersion(models.Model):
    offer = models.ForeignKey(Offer, on_delete=models.CASCADE, related_name="versions")
    created_at = models.DateTimeField(auto_now_add=True)
    snapshot_json = models.JSONField()  # зафиксированные поля + линии + вложения


# --- Критерии оценки ---

class CriterionType(models.TextChoices):
    NUMERIC_MIN = "NUM_MIN", "Числовой (минимизация)"
    NUMERIC_MAX = "NUM_MAX", "Числовой (максимизация)"
    CATEGORICAL = "CAT", "Категориальный"
    MANUAL = "MANUAL", "Ручной"

class CriterionSource(models.TextChoices):
    PRICE_TOTAL = "PRICE_TOTAL", "Итоговая цена"
    DELIVERY_DAYS = "DELIVERY_DAYS", "Срок поставки (дни)"
    WARRANTY_MONTHS = "WARRANTY_MONTHS", "Гарантия (мес.)"
    VALIDITY_DAYS = "VALIDITY_DAYS", "Валидность КП (дни)"
    PAYMENT_TERMS = "PAYMENT_TERMS", "Условия оплаты"
    MANUAL = "MANUAL", "Ручная оценка"

class Criterion(models.Model):
    tender = models.ForeignKey(Tender, on_delete=models.CASCADE, related_name="criteria")
    title = models.CharField("Название критерия", max_length=255)

    weight_percent = models.PositiveIntegerField("Вес (%)", validators=[MinValueValidator(0), MaxValueValidator(100)])
    ctype = models.CharField("Тип", max_length=20, choices=CriterionType.choices)
    source = models.CharField("Источник", max_length=30, choices=CriterionSource.choices)

    mandatory = models.BooleanField("Обязательный (pass/fail)", default=False)
    mandatory_hint = models.CharField("Правило обязательности (подсказка)", max_length=255, blank=True)

    # Для категориального: JSON словарь {"строка": балл0_100}
    category_scores = models.JSONField("Таблица баллов", default=dict, blank=True)

    def __str__(self):
        return f"{self.title} ({self.weight_percent}%)"

class ManualScore(models.Model):
    offer = models.ForeignKey(Offer, on_delete=models.CASCADE, related_name="manual_scores")
    criterion = models.ForeignKey(Criterion, on_delete=models.CASCADE, related_name="manual_scores")
    score_0_100 = models.PositiveIntegerField(validators=[MinValueValidator(0), MaxValueValidator(100)])
    comment = models.CharField("Комментарий", max_length=500, blank=True)

    class Meta:
        unique_together = [("offer", "criterion")]


# --- Q&A ---

class QaVisibility(models.TextChoices):
    ALL = "ALL", "Всем"
    PRIVATE = "PRIVATE", "Только задавшему"

class QuestionAnswer(models.Model):
    tender = models.ForeignKey(Tender, on_delete=models.CASCADE, related_name="qa")
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name="qa_questions")

    question = models.TextField("Вопрос")
    answer = models.TextField("Ответ", blank=True)

    visibility = models.CharField(max_length=10, choices=QaVisibility.choices, default=QaVisibility.ALL)

    created_at = models.DateTimeField(auto_now_add=True)
    answered_at = models.DateTimeField(null=True, blank=True)


# --- Уведомления и аудит ---

class EmailTemplate(models.Model):
    slug = models.SlugField(unique=True)
    subject = models.CharField("Тема", max_length=255)
    body = models.TextField("Тело письма (можно использовать {Переменные})")

    def __str__(self):
        return self.slug

class NotificationLog(models.Model):
    to_email = models.EmailField()
    template_slug = models.CharField(max_length=100)
    subject = models.CharField(max_length=255)
    status = models.CharField(max_length=20, default="OK")  # OK / FAIL
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class AuditLog(models.Model):
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    at = models.DateTimeField(auto_now_add=True)
    action = models.CharField(max_length=200)

    object_type = models.CharField(max_length=50, blank=True)
    object_id = models.CharField(max_length=50, blank=True)
    before = models.JSONField(default=dict, blank=True)
    after = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"{self.at} {self.action}"
