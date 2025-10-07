from django.contrib import admin
from .models import  User as CustomUser
from .models import SellerProfile,ClientProfile 
# Register your models here.
admin.site.register(CustomUser)
admin.site.register(SellerProfile)
admin.site.register(ClientProfile)
