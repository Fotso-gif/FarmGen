from . import views
from django.urls import path

urlpatterns = [
    path('my-shop/', views.shop_dashboard, name='marketplace_list'),
    path('create-shop/', views.create_shop, name='create_shop'),
    path('update-shop/', views.update_shop, name='update_shop'),
    path('create-category/', views.create_category, name='create_category'),
    path('create-product/', views.create_product, name='create_product'),
    path('history-commande/', views.order_history, name='history'),
    path('listing-commande/', views.order_listing, name='listing'),
    path('shop/<int:shop_id>', views.shop, name='shop'),
    path('favorite/<int:shop_id>/', views.toggle_favorite, name='toggle_favorite'),
    path('favorites/status/', views.favorites_status, name='favorites_status'),
    path('products/save/', views.create_update_product, name='save_product'),
    path('categories/save/', views.create_update_category, name='save_category'),
    path('api/products/<int:product_id>/', views.get_product, name='get_product'),
    path('api/categories/<int:category_id>/', views.get_category, name='get_category'),
    path('api/products/<int:product_id>/delete/', views.delete_product, name='delete_product'),
    path('api/categories/<int:category_id>/delete/', views.delete_category, name='delete_category'),
    path('api/products/<int:product_id>/duplicate/', views.duplicate_product, name='duplicate_product'),
    path('shop/update/', views.update_shop, name='update_shop'),
    #marketplace
    path('api/shop/<int:shop_id>/products/', views.shop_products_api, name='shop_products_api'),
    path('api/shop/<int:shop_id>/categories/', views.shop_categories_api, name='shop_categories_api'),
    path('api/products/<int:product_id>/like/', views.toggle_product_like, name='toggle_product_like'),
    path('api/products/<int:product_id>/view/', views.track_product_view, name='track_product_view'),
    # API endpoints
    path('api/shops/', views.api_shops, name='api_shops'),
    path('api/filters/', views.marketplace_filters, name='marketplace_filters'),
    path('api/search-history/', views.save_search_history, name='save_search_history'),
    # order
    path('orders/history/', views.order_history, name='order_history'),
    path('api/orders/<uuid:order_id>/update-status/', views.update_order_status, name='update_order_status'),
    path('orders/<uuid:order_id>/invoice/download/', views.download_invoice, name='download_invoice'),
    path('orders/export/<str:format_type>/', views.export_orders, name='export_orders'),
    path('orders/<uuid:order_id>/details/', views.order_details, name='order_details'),
    #
    # Détails d'une commande (AJAX)
    path('orders/<uuid:order_id>/detail/', views.order_detail, name='order_detail'),
    # Supprimer une commande
    path('orders/<uuid:order_id>/delete/', views.delete_order, name='delete_order'),
    
    # 
    path('orders/<uuid:order_id>/payment-proof/', views.payment_proof, name='payment_proof'),
    path('orders/export/<str:format>/', views.export_orders, name='export_orders'),# Methode de Paiement
    # Paiement
    path('api/payment-methods/', views.payment_methods_list, name='payment_methods_list'),
    path('api/payment-methods/create/', views.create_payment_method, name='create_payment_method'),
    # Statistiques
    path('statistiques/', views.shop_stat, name='stat'),
    # Export des données
    # path('dashboard/export/<str:format>/', views.export_dashboard_data, name='export_dashboard'),
    
    # API pour données dynamiques
    path('api/dashboard/stats/', views.dashboard_stats_api, name='dashboard_stats_api'),
    path('api/dashboard/charts/', views.dashboard_charts_api, name='dashboard_charts_api'),
]
#/api/payment-methods/create/',

