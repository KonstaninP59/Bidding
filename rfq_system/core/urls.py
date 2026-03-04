from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),

    # Auth
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("register-supplier/", views.register_supplier, name="register_supplier"),

    # Admin area (не django-admin)
    path("admin/users/", views.admin_users, name="admin_users"),
    path("admin/suppliers/", views.admin_suppliers, name="admin_suppliers"),
    path("admin/suppliers/<int:supplier_id>/", views.admin_supplier_review, name="admin_supplier_review"),
    path("admin/audit/", views.audit_list, name="audit_list"),
    path("admin/notifications/", views.notifications_list, name="notifications_list"),

    # Customer
    path("customer/tenders/", views.customer_tender_list, name="customer_tender_list"),
    path("customer/tenders/create/", views.customer_tender_create, name="customer_tender_create"),
    path("customer/tenders/<int:tender_id>/", views.customer_tender_detail, name="customer_tender_detail"),
    path("customer/tenders/<int:tender_id>/lots/", views.customer_tender_lots, name="customer_tender_lots"),
    path("customer/tenders/<int:tender_id>/items/", views.customer_tender_items, name="customer_tender_items"),
    path("customer/tenders/<int:tender_id>/criteria/", views.customer_tender_criteria, name="customer_tender_criteria"),
    path("customer/tenders/<int:tender_id>/invite/", views.customer_tender_invite, name="customer_tender_invite"),
    path("customer/tenders/<int:tender_id>/publish/", views.customer_tender_publish, name="customer_tender_publish"),
    path("customer/tenders/<int:tender_id>/rounds/", views.customer_tender_rounds, name="customer_tender_rounds"),
    path("customer/tenders/<int:tender_id>/compare/", views.customer_tender_compare, name="customer_tender_compare"),
    path("customer/tenders/<int:tender_id>/close/", views.customer_tender_close, name="customer_tender_close"),
    path("customer/tenders/<int:tender_id>/pdf/", views.customer_tender_pdf, name="customer_tender_pdf"),

    # Supplier
    path("supplier/profile/", views.supplier_profile, name="supplier_profile"),
    path("supplier/tenders/", views.supplier_tenders, name="supplier_tenders"),
    path("supplier/tenders/<int:tender_id>/", views.supplier_tender_detail, name="supplier_tender_detail"),
    path("supplier/tenders/<int:tender_id>/offer/<int:round_id>/", views.supplier_offer_edit, name="supplier_offer_edit"),
    path("supplier/tenders/<int:tender_id>/qa/", views.supplier_qa, name="supplier_qa"),

    # Invitation link (hybrid “C”)
    path("i/<str:token>/", views.invitation_landing, name="invitation_landing"),
    path("i/<str:token>/offer/", views.invitation_offer, name="invitation_offer"),
    path("i/<str:token>/create-account/", views.invitation_create_account, name="invitation_create_account"),
]
