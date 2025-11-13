from django.urls import path
from . import views
from django.conf import settings
from django.http import JsonResponse

urlpatterns = [
    # Page UI
    path('panier/', views.cart_page, name='cart-page'),
    path('checkout/', views.checkout_page, name='checkout-page'),
    path('process/<str:payment_method>/', views.process_checkout, name='process-checkout'),
    path('upload-proof/<uuid:order_id>/', views.upload_payment_proof, name='upload-payment-proof'),
    path('verify-payment/<uuid:order_id>/', views.verify_payment_manual, name='verify-payment'),
    path('order/status/<uuid:order_id>/', views.order_status, name='order-status'),

]
