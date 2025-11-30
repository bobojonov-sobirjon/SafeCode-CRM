from rest_framework import serializers
from .models import Order, OrderItem, DeliveryMethod, PaymentMethod
from apps.v1.products.models import Product


class DeliveryMethodSerializer(serializers.ModelSerializer):
    """
    Сериализатор для способа доставки
    """
    class Meta:
        model = DeliveryMethod
        fields = ['id', 'name', 'details', 'price', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class DeliveryMethodCreateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для создания способа доставки
    """
    class Meta:
        model = DeliveryMethod
        fields = ['name', 'details', 'price']
        extra_kwargs = {
            'details': {'required': False, 'allow_blank': True, 'allow_null': True},
            'price': {'required': False}
        }


class PaymentMethodSerializer(serializers.ModelSerializer):
    """
    Сериализатор для способа оплаты
    """
    class Meta:
        model = PaymentMethod
        fields = ['id', 'name', 'details', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class PaymentMethodCreateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для создания способа оплаты
    """
    class Meta:
        model = PaymentMethod
        fields = ['name', 'details']
        extra_kwargs = {
            'details': {'required': False, 'allow_blank': True, 'allow_null': True}
        }


class OrderItemSerializer(serializers.ModelSerializer):
    """
    Сериализатор для элемента заказа
    """
    product = serializers.SerializerMethodField()
    
    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'quantity', 'created_at']
        read_only_fields = ['id', 'created_at']
    
    def get_product(self, obj):
        """
        Получение информации о продукте
        """
        return {
            'id': obj.product.id,
            'name': obj.product.name,
            'price': str(obj.product.price) if obj.product.price else None,
            'article': obj.product.article,
        }


class OrderItemCreateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для создания элемента заказа
    """
    class Meta:
        model = OrderItem
        fields = ['product_id', 'quantity']
    
    product_id = serializers.IntegerField(write_only=True)
    
    def validate_product_id(self, value):
        """
        Проверка существования продукта
        """
        if not Product.objects.filter(id=value, is_active=True, is_deleted=False).exists():
            raise serializers.ValidationError('Продукт не найден или неактивен.')
        return value
    
    def create(self, validated_data):
        """
        Создание элемента заказа
        """
        product_id = validated_data.pop('product_id')
        product = Product.objects.get(id=product_id)
        validated_data['product'] = product
        return super().create(validated_data)


class OrderSerializer(serializers.ModelSerializer):
    """
    Сериализатор для чтения заказа
    """
    items = OrderItemSerializer(many=True, read_only=True)
    delivery_method = serializers.SerializerMethodField()
    payment_method = serializers.SerializerMethodField()
    user = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'user', 'city', 'street', 'house',
            'apartment', 'postal_index', 'status', 'delivery_method',
            'payment_method', 'total_price', 'items', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'order_number', 'created_at', 'updated_at', 'items']
    
    def get_delivery_method(self, obj):
        """
        Получение информации о способе доставки
        """
        if obj.delivery_method:
            return {
                'id': obj.delivery_method.id,
                'name': obj.delivery_method.name,
                'details': obj.delivery_method.details,
                'price': str(obj.delivery_method.price) if obj.delivery_method.price else None,
            }
        return None
    
    def get_payment_method(self, obj):
        """
        Получение информации о способе оплаты
        """
        if obj.payment_method:
            return {
                'id': obj.payment_method.id,
                'name': obj.payment_method.name,
                'details': obj.payment_method.details,
            }
        return None
    
    def get_user(self, obj):
        """
        Получение информации о пользователе
        """
        return {
            'id': obj.user.id,
            'email': obj.user.email,
            'first_name': obj.user.first_name,
            'last_name': obj.user.last_name,
        }


class OrderCreateSerializer(serializers.Serializer):
    """
    Сериализатор для создания заказа
    """
    city = serializers.CharField(required=True, max_length=255)
    street = serializers.CharField(required=True, max_length=255)
    house = serializers.CharField(required=True, max_length=50)
    apartment = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=50)
    postal_index = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=20)
    delivery_method_id = serializers.IntegerField(required=False, allow_null=True)
    payment_method_id = serializers.IntegerField(required=False, allow_null=True)
    items = OrderItemCreateSerializer(many=True, required=True, min_length=1)
    
    def validate_delivery_method_id(self, value):
        """
        Проверка существования способа доставки
        """
        if value is not None:
            if not DeliveryMethod.objects.filter(id=value).exists():
                raise serializers.ValidationError('Способ доставки не найден.')
        return value
    
    def validate_payment_method_id(self, value):
        """
        Проверка существования способа оплаты
        """
        if value is not None:
            if not PaymentMethod.objects.filter(id=value).exists():
                raise serializers.ValidationError('Способ оплаты не найден.')
        return value
    
    def create(self, validated_data):
        """
        Создание заказа
        """
        from decimal import Decimal
        
        user = self.context['request'].user
        items_data = validated_data.pop('items')
        delivery_method_id = validated_data.pop('delivery_method_id', None)
        payment_method_id = validated_data.pop('payment_method_id', None)
        
        # Получаем способы доставки и оплаты
        delivery_method = None
        if delivery_method_id:
            delivery_method = DeliveryMethod.objects.get(id=delivery_method_id)
        
        payment_method = None
        if payment_method_id:
            payment_method = PaymentMethod.objects.get(id=payment_method_id)
        
        # Создаем заказ
        order = Order.objects.create(
            user=user,
            city=validated_data['city'],
            street=validated_data['street'],
            house=validated_data['house'],
            apartment=validated_data.get('apartment'),
            postal_index=validated_data.get('postal_index'),
            delivery_method=delivery_method,
            payment_method=payment_method,
            status=Order.PaymentStatus.PENDING
        )
        
        # Создаем элементы заказа и вычисляем общую цену
        total_price = Decimal('0')
        if delivery_method and delivery_method.price:
            total_price += delivery_method.price
        
        for item_data in items_data:
            product_id = item_data['product_id']
            quantity = item_data['quantity']
            product = Product.objects.get(id=product_id)
            
            # Создаем элемент заказа
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=quantity
            )
            
            # Добавляем к общей цене
            if product.price:
                total_price += product.price * quantity
        
        # Обновляем общую цену заказа
        order.total_price = total_price
        order.save()
        
        return order

