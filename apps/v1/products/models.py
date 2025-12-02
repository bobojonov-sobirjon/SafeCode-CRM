from django.db import models
from django.conf import settings

class Category(models.Model):
    name = models.CharField(max_length=255, verbose_name="Название категории", null=True, blank=True)
    description = models.TextField(blank=True, null=True, verbose_name="Описание категории")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    
    objects = models.Manager()
    
    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "01. Категории"
        indexes = [
            models.Index(fields=['-created_at'], name='category_created_idx'),
        ]
        
    def __str__(self):
        return self.name or f"Category {self.id}"


class Product(models.Model):
    name = models.CharField(max_length=255, verbose_name="Название продукта", null=True, blank=True)
    description = models.TextField(blank=True, null=True, verbose_name="Описание продукта")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, verbose_name="Категория", null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена", null=True, blank=True)
    article = models.CharField(max_length=255, verbose_name="Артикул", null=True, blank=True)
    stock = models.IntegerField(verbose_name="Количество на складе", null=True, blank=True)
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    is_deleted = models.BooleanField(default=False, verbose_name="Удален")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    
    objects = models.Manager()
    
    class Meta:
        verbose_name = "Продукт"
        verbose_name_plural = "02. Продукты"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['category', '-created_at'], name='product_category_created_idx'),
            models.Index(fields=['is_active', 'is_deleted', '-created_at'], name='product_active_deleted_idx'),
            models.Index(fields=['article'], name='product_article_idx'),
        ]
    
    def __str__(self):
        return self.name or f"Product {self.id}"


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Продукт", null=True, blank=True)
    image = models.ImageField(upload_to='products/', verbose_name="Изображение продукта", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    
    objects = models.Manager()
    
    class Meta:
        verbose_name = "Изображение продукта"
        verbose_name_plural = "Изображения продуктов"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['product', '-created_at'], name='pi_product_created_idx'),
        ]
        
    def __str__(self):
        return self.product.name if self.product else f"Image {self.id}"
    

class ProductSizes(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Продукт", null=True, blank=True)
    width = models.IntegerField(verbose_name="Ширина", null=True, blank=True)
    height = models.IntegerField(verbose_name="Высота", null=True, blank=True)
    depth = models.IntegerField(verbose_name="Глубина", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    
    objects = models.Manager()
    
    class Meta:
        verbose_name = "Характеристика продукта"


class FavoriteProduct(models.Model):
    """
    Модель для избранных продуктов пользователя
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='favorite_products',
        verbose_name='Пользователь'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='favorites',
        verbose_name='Продукт'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    
    objects = models.Manager()
    
    class Meta:
        verbose_name = "Избранный продукт"
        verbose_name_plural = "Избранные продукты"
        ordering = ['-created_at']
        unique_together = ('user', 'product')  # Один пользователь не может добавить один продукт дважды
        indexes = [
            models.Index(fields=['user', '-created_at'], name='fp_user_created_idx'),
            models.Index(fields=['product'], name='fp_product_idx'),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.product.name}"
