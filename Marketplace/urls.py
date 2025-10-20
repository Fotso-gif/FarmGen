from . import views
from django.urls import path

urlpatterns = [
    path('', views.index, name='marketplace_list'),
    path('shop/<int:shop_id>', views.shop, name='shop'),
]