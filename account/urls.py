from . import views
from django.urls import path

urlpatterns = [
    path('login/traitement/', views.login_api, name='login'),
    path('register/traitement/', views.register_api, name='register'),
    # Réinitialisation de mot de passe
    path('forgot-password/api/', views.forgot_password_api, name='forgot_password_api'),
    path('reset-password-email/', views.reset_password_email_sent_view, name='reset_password_email'),
    path('reset-password-confirm/<str:token>/', views.reset_password_confirm_view, name='reset_password_confirm'),
    path('reset-password-confirm/<str:token>/api/', views.reset_password_confirm_api, name='reset_password_confirm_api'),
     # Vérification d'email
    path('verify-email/<str:token>/', views.verify_email_view, name='verify_email'),
    path('verification-sent/', views.verification_sent_view, name='verification_sent'),
    path('resend-verification/api/', views.resend_verification_email_api, name='resend_verification'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('profile/', views.profile, name='profile'),
    path('update/password', views.update_password, name='update_password'),
]