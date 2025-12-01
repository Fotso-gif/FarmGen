from django.shortcuts import render
from .models import Article

def liste_articles(request):
    articles = Article.objects.all().order_by('-date_publication')
    return render(request, 'blog/liste_articles.html', {'articles': articles})

def blog_admin(request):
    return render(request, 'blog/blogAdmin.html')
