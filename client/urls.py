from . import views
from django.urls import path

urlpatterns = [
    path('', views.index, name='home'),
    path('login/', views.login, name='login_view'),
    path('register/', views.register, name='register_view'),
    path('reset_password/', views.forgot_password, name='forgot-password'),
    path('marketplace/', views.marketplace, name='marketplace'),
    path('search/', views.search_shops, name='search_shops'),
    path('blog/', views.blog, name='blog'),
    path('blog/article/<int:article_id>/', views.article_detail, name='article_detail'),
    #Newsletter
    path('subscribe/', views.NewsletterSubscribeView.as_view(), name='subscribe_newsletter'),
    path('confirm/<str:token>/', views.NewsletterConfirmView.as_view(), name='confirm_newsletter'),
    path('unsubscribe/<str:token>/', views.NewsletterUnsubscribeView.as_view(), name='unsubscribe_newsletter'),
    path('Newsletter/stats/', views.NewsletterStatsView.as_view(), name='newsletter_stats'),
]