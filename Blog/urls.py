from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from Blog import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.liste_articles, name='liste_articles'),
    path('list/', views.seller_blog, name='seller_blog'),
    path('create/', views.create_article, name='create_article'),
    path('article/<int:article_id>/edit/', views.edit_article, name='edit_article'),
    path('article/<int:article_id>/delete/', views.delete_article, name='delete_article'),
    path('article/<int:article_id>/preview/', views.article_preview, name='article_preview'),
    path('preview/', views.article_preview, name='article_preview_generic'),
     path('api/carousel/', views.BlogCarouselAPIView.as_view(), name='blog_carousel_api'),
]

# if settings.DEBUG:
#     urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
