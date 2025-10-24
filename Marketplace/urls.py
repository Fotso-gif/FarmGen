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
    path('orders/export/<str:format>/', views.export_orders, name='export_orders'),
    path('api/orders/<int:order_id>/update-status/', views.update_order_status, name='update_order_status'),
]