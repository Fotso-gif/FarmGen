from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json
from .models import Shop, Product, Favorite
# Create your views here.
def index(request):
    render(request, 'marketplace/index.html')

def history(request):
    render(request, 'marketplace/historiqueCommande.html')
    
def shop(request, shop_id):
    shop = Shop.objects.get(id = shop_id)
    produits = Product.objects.filter(category__shop=shop)
    return render(request, 'marketplace/e_shop.html', {'produits': produits, 'shop': shop})    

@login_required
@require_POST
@csrf_exempt
def toggle_favorite(request, shop_id):
    try:
        shop = Shop.objects.get(id=shop_id)
        favorite, created = Favorite.objects.get_or_create(
            user=request.user,
            shop=shop
        )
        
        if not created:
            # Si déjà favori, on supprime
            favorite.delete()
            return JsonResponse({
                'status': 'removed',
                'message': 'Boutique retirée des favoris',
                'is_favorite': False
            })
        
        return JsonResponse({
            'status': 'added',
            'message': 'Boutique ajoutée aux favoris',
            'is_favorite': True
        })
        
    except Shop.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Boutique non trouvée'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@login_required
def get_favorites_status(request):
    """Récupère le statut favori des boutiques pour l'utilisateur connecté"""
    favorite_shop_ids = Favorite.objects.filter(
        user=request.user
    ).values_list('shop_id', flat=True)
    
    return JsonResponse({
        'favorites': list(favorite_shop_ids)
})
    
"""from rest_framework import viewsets, status, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Category, Product, ProductImage
from .serializers import CategorySerializer, ProductSerializer, ProductCreateUpdateSerializer, ProductImageSerializer
from .filters import ProductFilter
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter, SearchFilter
from django.db.models import Sum, F
from django.utils import timezone

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    lookup_field = "id"

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.prefetch_related("images").all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ProductFilter
    search_fields = ["name", "description"]
    ordering_fields = ["price", "quantity", "expiry_date"]
    def get_serializer_class(self):
        if self.action in ["create","update","partial_update"]: return ProductCreateUpdateSerializer
        return ProductSerializer
    @action(detail=False, methods=["get"])
    def low_stock(self, request):
        threshold = int(request.query_params.get("threshold", Product.LOW_STOCK_THRESHOLD))
        items = Product.objects.filter(quantity__lt=threshold)
        serializer = ProductSerializer(items, many=True, context={"request": request})
        return Response(serializer.data)
    @action(detail=False, methods=["get"])
    def expired(self, request):
        today = timezone.localdate()
        items = Product.objects.filter(expiry_date__lt=today)
        serializer = ProductSerializer(items, many=True, context={"request": request})
        return Response(serializer.data)
    @action(detail=False, methods=["get"])
    def report(self, request):
        total_products = Product.objects.count()
        total_value = Product.objects.aggregate(total_value=Sum(F("price") * F("quantity")))["total_value"] or 0
        most_expensive = Product.objects.order_by("-price").first()
        cheapest = Product.objects.order_by("price").first()
        def serialize_simple(p): return {"id": p.id, "name": p.name, "price": str(p.price), "quantity": p.quantity} if p else None
        return Response({"total_products": total_products,"total_stock_value": str(total_value),"most_expensive": serialize_simple(most_expensive),"cheapest": serialize_simple(cheapest)})
class ProductImageViewSet(mixins.CreateModelMixin, mixins.DestroyModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = ProductImage.objects.select_related("product").all()
    serializer_class = ProductImageSerializer
"""