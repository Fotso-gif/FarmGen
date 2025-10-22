from . import views
from django.urls import path

urlpatterns = [
    path('my-shop/', views.index, name='marketplace_list'),
    path('history-commande/', views.history, name='history'),
    path('shop/<int:shop_id>', views.shop, name='shop'),
    path('favorite/<int:shop_id>/', views.toggle_favorite, name='toggle_favorite'),
    path('favorites/status/', views.get_favorites_status, name='favorites_status'),
]