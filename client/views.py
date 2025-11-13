from django.shortcuts import render
from Marketplace.models import Shop

# Create your views here.
def index(request):
    return render(request, 'client/index.html')

def login(request):
    return render(request, 'client/auth/login.html')

def register(request):
    return render(request, 'client/auth/register.html')

def forgot_password(request):
    return render(request, 'client/auth/forgot-password.html')

def marketplace(request):
    shops = Shop.objects.all()
    return render(request, 'client/marketplace.html', {'shops':shops})

def blog(request):
    return render(request, 'client/blog.html')
