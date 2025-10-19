from rest_framework import serializers

class CartItemSerializer(serializers.Serializer):
    product_id = serializers.CharField()
    name = serializers.CharField()
    price = serializers.IntegerField()  # price in cents
    quantity = serializers.IntegerField(min_value=1)

class CheckoutSerializer(serializers.Serializer):
    currency = serializers.CharField(default='usd')
    # amount optional (server may compute); if client passes, it's cents
    amount = serializers.IntegerField(required=False)
    payment_method = serializers.CharField(required=False)
