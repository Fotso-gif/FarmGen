from . import views
from django.urls import path

urlpatterns = [
    path('login/', views.login_api, name='login'),
    path('register/', views.register_api, name='register'),
]