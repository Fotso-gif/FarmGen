from . import views
from django.urls import path

urlpatterns = [
    path('login/traitement/', views.login_api, name='login'),
    path('register/traitement/', views.register_api, name='register'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
]