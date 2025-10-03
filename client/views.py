from django.shortcuts import render

# Create your views here.
def index(request):
    return render(request, 'client/index.html')

def login(request):
    return render(request, 'client/auth/login.html')

def register(request):
    return render(request, 'client/auth/register.html')

def reset_password(request):
    return render(request, 'client/auth/reset-password.html')

