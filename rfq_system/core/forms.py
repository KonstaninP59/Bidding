from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from django.conf import settings
from .models import (
    Supplier, SupplierDocument,
    Tender, TenderFile, Lot, Item,
    Criterion, TenderRound,
    Offer, OfferLine, OfferAttachment,
    ManualScore, QuestionAnswer,
    UserProfile, UserRole, AccreditationStatus
)

class RuAuthForm(AuthenticationForm):
    username = forms.EmailField(label="Email")
    password = forms.CharField(label="Пароль", widget=forms.PasswordInput)

class SupplierRegisterForm(forms.Form):
    email = forms.EmailField(label="Email")
    password1 = forms.CharField(label="Пароль", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Повтор пароля", widget=forms.PasswordInput)

    company_name = forms.CharField(label="Наименование компании", max_length=255)

    def clean(self):
        data = super().clean()
        if data.get("password1") != data.get("password2"):
            raise forms.ValidationError("Пароли не совпадают.")
        if User.objects.filter(username=data.get("email")).exists():
            raise forms.ValidationError("Пользователь с таким Email уже существует.")
        return data

class SupplierProfileForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ["company_name", "inn", "kpp", "ogrn", "address", "contacts", "categories", "accreditation_status"]
        widgets = {
            "contacts": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Поставщик сам не должен ставить "Аккредитован/Отказ"
        self.fields["accreditation_status"].choices = [
            (AccreditationStatus.DRAFT, "Черновик"),
            (AccreditationStatus.REVIEW, "На проверке"),
        ]

class SupplierDocumentForm(forms.ModelForm):
    class Meta:
        model = SupplierDocument
        fields = ["doc_type", "file", "expires_at", "comment"]

    def clean_file(self):
        f = self.cleaned_data.get("file")
        if f and f.size > settings.MAX_UPLOAD_MB * 1024 * 1024:
            raise forms.ValidationError(f"Файл слишком большой. Максимум: {settings.MAX_UPLOAD_MB} МБ.")
        return f

class TenderForm(forms.ModelForm):
    class Meta:
        model = Tender
        fields = [
            "title", "description", "currency",
            "with_lots", "allow_alternatives", "allow_partial", "price_format",
            "supplier_sees_rank",
        ]
        widgets = {"description": forms.Textarea(attrs={"rows": 4})}

class TenderFileForm(forms.ModelForm):
    class Meta:
        model = TenderFile
        fields = ["title", "file"]

    def clean_file(self):
        f = self.cleaned_data.get("file")
        if f and f.size > settings.MAX_UPLOAD_MB * 1024 * 1024:
            raise forms.ValidationError(f"Файл слишком большой. Максимум: {settings.MAX_UPLOAD_MB} МБ.")
        return f

class LotForm(forms.ModelForm):
    class Meta:
        model = Lot
        fields = ["title", "description", "place", "terms"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3}), "terms": forms.Textarea(attrs={"rows": 3})}

class ItemForm(forms.ModelForm):
    class Meta:
        model = Item
        fields = ["lot", "name", "qty", "unit", "requirements"]
        widgets = {"requirements": forms.Textarea(attrs={"rows": 3})}

class CriterionForm(forms.ModelForm):
    category_scores_text = forms.CharField(
        label="Таблица баллов (для категориального)",
        required=False,
        help_text="Формат: каждая строка = значение=балл. Пример: '100% предоплата=20'",
        widget=forms.Textarea(attrs={"rows": 4}),
    )

    class Meta:
        model = Criterion
        fields = ["title", "weight_percent", "ctype", "source", "mandatory", "mandatory_hint"]

    def clean(self):
        data = super().clean()
        ctype = data.get("ctype")
        source = data.get("source")
        if ctype == "MANUAL" and source != "MANUAL":
            raise forms.ValidationError("Для ручного критерия источник должен быть 'Ручная оценка'.")
        if ctype != "MANUAL" and source == "MANUAL":
            raise forms.ValidationError("Источник 'Ручная оценка' допустим только для ручного критерия.")
        return data

    def parse_category_scores(self):
        """
        Превращаем text в dict {"значение": score}
        """
        text = (self.cleaned_data.get("category_scores_text") or "").strip()
        result = {}
        if not text:
            return result
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            if "=" not in line:
                raise forms.ValidationError("Неверный формат таблицы баллов: используйте value=score")
            value, score = line.split("=", 1)
            value = value.strip()
            score = int(score.strip())
            if score < 0 or score > 100:
                raise forms.ValidationError("Балл должен быть в диапазоне 0..100")
            result[value] = score
        return result

class RoundCreateForm(forms.ModelForm):
    class Meta:
        model = TenderRound
        fields = ["start_at", "deadline_at"]
        widgets = {
            "start_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "deadline_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }

class OfferForm(forms.ModelForm):
    class Meta:
        model = Offer
        fields = ["delivery_days", "payment_terms", "warranty_months", "validity_days", "deviations", "comment"]
        widgets = {
            "deviations": forms.Textarea(attrs={"rows": 3}),
            "comment": forms.Textarea(attrs={"rows": 3}),
        }

class OfferAttachmentForm(forms.ModelForm):
    class Meta:
        model = OfferAttachment
        fields = ["title", "file"]

    def clean_file(self):
        f = self.cleaned_data.get("file")
        if f and f.size > settings.MAX_UPLOAD_MB * 1024 * 1024:
            raise forms.ValidationError(f"Файл слишком большой. Максимум: {settings.MAX_UPLOAD_MB} МБ.")
        return f

class ManualScoreForm(forms.ModelForm):
    class Meta:
        model = ManualScore
        fields = ["score_0_100", "comment"]

class QaAskForm(forms.ModelForm):
    class Meta:
        model = QuestionAnswer
        fields = ["question"]
        widgets = {"question": forms.Textarea(attrs={"rows": 3})}

class QaAnswerForm(forms.ModelForm):
    class Meta:
        model = QuestionAnswer
        fields = ["answer", "visibility"]
        widgets = {"answer": forms.Textarea(attrs={"rows": 3})}
