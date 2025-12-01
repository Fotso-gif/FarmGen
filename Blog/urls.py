from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from Blog import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.liste_articles, name='liste_articles'),
    path('list/', views.blog_admin, name='blog_admin'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
