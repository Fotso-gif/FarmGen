from . import views
from django.urls import path

urlpatterns = [
    path('my-shop/', views.shop_dashboard, name='marketplace_list'),
    path('create-shop/', views.create_shop, name='create_shop'),
    path('update-shop/', views.update_shop, name='update_shop'),
    path('create-category/', views.create_category, name='create_category'),
    path('create-product/', views.create_product, name='create_product'),
    path('history-commande/', views.order_history, name='history'),
    path('shop/<int:shop_id>', views.shop, name='shop'),
    path('favorite/<int:shop_id>/', views.toggle_favorite, name='toggle_favorite'),
    path('favorites/status/', views.get_favorites_status, name='favorites_status'),
    path('products/save/', views.create_update_product, name='save_product'),
    path('categories/save/', views.create_update_category, name='save_category'),
    path('api/products/<int:product_id>/', views.get_product, name='get_product'),
    path('api/categories/<int:category_id>/', views.get_category, name='get_category'),
    path('api/products/<int:product_id>/delete/', views.delete_product, name='delete_product'),
    path('api/categories/<int:category_id>/delete/', views.delete_category, name='delete_category'),
    path('api/products/<int:product_id>/duplicate/', views.duplicate_product, name='duplicate_product'),
    path('shop/update/', views.update_shop, name='update_shop'),
    # order
    path('orders/history/', views.order_history, name='order_history'),
    path('api/orders/<uuid:order_id>/update-status/', views.update_order_status, name='update_order_status'),
    # path('orders/<uuid:order_id>/details/', views.order_details, name='order_details'),
    # path('orders/<uuid:order_id>/payment-proof/', views.payment_proof, name='payment_proof'),
    path('orders/export/<str:format>/', views.export_orders, name='export_orders'),# Methode de Paiement
    # Paiement
    path('api/payment-methods/', views.payment_methods_list, name='payment_methods_list'),
    path('api/payment-methods/create/', views.create_payment_method, name='create_payment_method'),
]
#/api/payment-methods/create/',

