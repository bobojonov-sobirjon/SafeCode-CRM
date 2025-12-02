from rest_framework import serializers
from .models import Product, ProductImage, ProductSizes, FavoriteProduct, Category


class CategorySerializer(serializers.ModelSerializer):
    """
    Сериализатор для категории
    """
    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
        

class ProductImageSerializer(serializers.ModelSerializer):
    """
    Сериализатор для изображений продукта
    """
    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class ProductSizesSerializer(serializers.ModelSerializer):
    """
    Сериализатор для размеров продукта
    """
    class Meta:
        model = ProductSizes
        fields = ['id', 'width', 'height', 'depth', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class ProductSerializer(serializers.ModelSerializer):
    """
    Сериализатор для продукта (чтение)
    """
    images_list = serializers.SerializerMethodField()
    sizes_list = serializers.SerializerMethodField()
    category = CategorySerializer(read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'price', 'stock', 'article',
            'is_active', 'is_deleted', 'created_at', 'updated_at',
            'images_list', 'sizes_list', 'category'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_images_list(self, obj):
        """
        Получение списка изображений продукта
        Prefetch_related ishlatilgan, shuning uchun N+1 query muammosi yo'q
        """
        # Prefetch_related orqali allaqachon yuklangan
        if hasattr(obj, 'productimage_set'):
            images = obj.productimage_set.all()
        else:
            images = ProductImage.objects.filter(product=obj)
        return ProductImageSerializer(images, many=True, context=self.context).data
    
    def get_sizes_list(self, obj):
        """
        Получение списка размеров продукта
        """
        # Prefetch_related qo'shish kerak bo'lsa, views.py da qo'shiladi
        sizes = ProductSizes.objects.filter(product=obj)
        return ProductSizesSerializer(sizes, many=True, context=self.context).data
    
    def get_category(self, obj):
        """
        Получение категории продукта
        """
        return CategorySerializer(obj.category, context=self.context).data


class ProductCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для создания и обновления продукта
    Поддерживает form-data для загрузки изображений
    """
    images_list = serializers.ListField(
        child=serializers.ImageField(),
        required=False,
        allow_empty=True,
        write_only=True
    )
    width = serializers.IntegerField(required=False, allow_null=True, write_only=True)
    height = serializers.IntegerField(required=False, allow_null=True, write_only=True)
    depth = serializers.IntegerField(required=False, allow_null=True, write_only=True)
    
    class Meta:
        model = Product
        fields = [
            'name', 'description', 'price', 'stock', 'article',
            'is_active', 'images_list', 'width', 'height', 'depth', 'category'
        ]
    
    def to_internal_value(self, data):
        """
        Обработка form-data для images_list
        """
        request = self.context.get('request')
        if request and hasattr(request, 'FILES'):
            files = request.FILES
            images_files = files.getlist('images_list')
            if images_files:
                if hasattr(data, 'copy'):
                    mutable_data = data.copy()
                elif isinstance(data, dict):
                    mutable_data = data.copy()
                else:
                    mutable_data = dict(data)
                mutable_data['images_list'] = images_files
                data = mutable_data
        
        return super().to_internal_value(data)
    
    def create(self, validated_data):
        """
        Создание продукта с изображениями и размерами
        """
        images_list = validated_data.pop('images_list', [])
        width = validated_data.pop('width', None)
        height = validated_data.pop('height', None)
        depth = validated_data.pop('depth', None)
        
        # Создаем продукт
        product = Product.objects.create(**validated_data)
        
        # Bulk create ishlatilmoqda - tezroq ishlash uchun
        if images_list:
            images = [
                ProductImage(product=product, image=image)
                for image in images_list
            ]
            ProductImage.objects.bulk_create(images)
        
        # Создаем размеры если указаны
        if width is not None or height is not None or depth is not None:
            ProductSizes.objects.create(
                product=product,
                width=width,
                height=height,
                depth=depth
            )
        
        return product
    
    def update(self, instance, validated_data):
        """
        Обновление продукта с изображениями и размерами
        """
        images_list = validated_data.pop('images_list', None)
        width = validated_data.pop('width', None)
        height = validated_data.pop('height', None)
        depth = validated_data.pop('depth', None)
        
        # Обновляем основные поля продукта
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Обновляем изображения если указаны
        if images_list is not None:
            # Удаляем старые изображения
            ProductImage.objects.filter(product=instance).delete()
            # Bulk create ishlatilmoqda - tezroq ishlash uchun
            if images_list:
                images = [
                    ProductImage(product=instance, image=image)
                    for image in images_list
                ]
                ProductImage.objects.bulk_create(images)
        
        # Обновляем размеры если указаны
        if width is not None or height is not None or depth is not None:
            sizes, created = ProductSizes.objects.get_or_create(product=instance)
            if width is not None:
                sizes.width = width
            if height is not None:
                sizes.height = height
            if depth is not None:
                sizes.depth = depth
            sizes.save()
        
        return instance


class FavoriteProductSerializer(serializers.ModelSerializer):
    """
    Сериализатор для избранных продуктов
    """
    product = ProductSerializer(read_only=True)
    product_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = FavoriteProduct
        fields = ['id', 'product', 'product_id', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_product_id(self, value):
        """
        Проверка существования продукта
        """
        if not Product.objects.filter(id=value, is_deleted=False).exists():
            raise serializers.ValidationError('Продукт не найден или удален.')
        return value
    
    def create(self, validated_data):
        """
        Создание избранного продукта
        """
        product_id = validated_data.pop('product_id')
        user = self.context['request'].user
        
        # Проверяем, не добавлен ли уже этот продукт в избранное
        if FavoriteProduct.objects.filter(user=user, product_id=product_id).exists():
            raise serializers.ValidationError('Этот продукт уже добавлен в избранное.')
        
        product = Product.objects.get(id=product_id)
        favorite = FavoriteProduct.objects.create(user=user, product=product)
        return favorite

