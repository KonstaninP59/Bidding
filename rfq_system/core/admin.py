from django.contrib import admin
from .models import (
    UserProfile, Supplier, SupplierDocument,
    Tender, TenderFile, Lot, Item,
    TenderRound, TenderInvitation,
    Offer, OfferLine, OfferAttachment, OfferVersion,
    Criterion, ManualScore,
    QuestionAnswer,
    EmailTemplate, NotificationLog, AuditLog
)

admin.site.site_header = "Администрирование RFQ"

admin.site.register(UserProfile)
admin.site.register(Supplier)
admin.site.register(SupplierDocument)

admin.site.register(Tender)
admin.site.register(TenderFile)
admin.site.register(Lot)
admin.site.register(Item)

admin.site.register(TenderRound)
admin.site.register(TenderInvitation)

admin.site.register(Offer)
admin.site.register(OfferLine)
admin.site.register(OfferAttachment)
admin.site.register(OfferVersion)

admin.site.register(Criterion)
admin.site.register(ManualScore)

admin.site.register(QuestionAnswer)

admin.site.register(EmailTemplate)
admin.site.register(NotificationLog)
admin.site.register(AuditLog)
