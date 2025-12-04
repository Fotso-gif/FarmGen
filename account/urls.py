from . import views
from django.urls import path

urlpatterns = [
    path('login/traitement/', views.login_api, name='login'),
    path('register/traitement/', views.register_api, name='register'),
    path('logout/', views.logout_view, name='logout'),
    # Réinitialisation de mot de passe
    path('forgot-password/api/', views.forgot_password_api, name='forgot_password_api'),
    path('reset-password-email/', views.reset_password_email_sent_view, name='reset_password_email'),
    path('reset-password-confirm/<str:token>/', views.reset_password_confirm_view, name='reset_password_confirm'),
    path('reset-password-confirm/<str:token>/api/', views.reset_password_confirm_api, name='reset_password_confirm_api'),
     # Vérification d'email
    path('verify-email/<str:token>/', views.verify_email_view, name='verify_email'),
    path('verification-sent/', views.verification_sent_view, name='verification_sent'),
    path('resend-verification/api/', views.resend_verification_email_api, name='resend_verification'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profile/', views.profile, name='profile'),
    path("update-avatar/", views.update_avatar, name="update-avatar"),
    path('update/password', views.update_password, name='update_password'),
     # Product
    path('api/products/<int:product_id>/', views.get_product_data, name='get_product_data'),
    path('api/products/create/', views.create_product, name='create_product_api'),
    #path('api/orders/<uuid:order_id>/', views.get_order_data, name='get_order_data'),
    # API endpoints pour les modals
    path('api/shop/<int:shop_id>/', views.api_shop_detail, name='api_shop_detail'),
    path('api/products/<int:product_id>/', views.api_product_detail, name='api_product_detail'),
    path('api/products/<int:product_id>/update/', views.api_product_update, name='api_product_update'),
    path('api/orders/<uuid:order_id>/', views.api_order_detail, name='api_order_detail'),
    path('api/orders/<uuid:order_id>/update/', views.api_order_update, name='api_order_update'),
    path('api/statistics/', views.api_statistics, name='api_statistics'),
    path('api/shop/<int:shop_id>/categories/', views.api_shop_categories, name='api_shop_categories'),
    path('api/products/<int:product_id>/update-advanced/', views.api_product_update_advanced, name='api_product_update_advanced'),
]