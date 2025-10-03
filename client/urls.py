from . import views
from django.urls import path

urlpatterns = [
    path('', views.index, name='home'),
    path('login/', views.login, name='login_view'),
    path('register/', views.register, name='register_view'),
    path('reset_password/', views.reset_password, name='reset-password'),
]