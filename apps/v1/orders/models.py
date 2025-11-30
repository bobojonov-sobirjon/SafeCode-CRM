from django.db import models
from django.conf import settings
from django.utils import timezone
import random
import string


def generate_order_number():
    """
    Генерация номера заказа: буквы и цифры, заглавные буквы
    """
    letters = ''.join(random.choices(string.ascii_uppercase, k=4))
    numbers = ''.join(random.choices(string.digits, k=6))
    return f"{letters}{numbers}"


class DeliveryMethod(models.Model):
    """
    Способ доставки
    """
    name = models.CharField(max_length=255, verbose_name='Название')
    details = models.TextField(blank=True, null=True, verbose_name='Детали')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Цена', default=0)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    
    class Meta:
        verbose_name = 'Способ доставки'
        verbose_name_plural = 'Способы доставки'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name


class PaymentMethod(models.Model):
    """
    Способ оплаты
    """
    name = models.CharField(max_length=255, verbose_name='Название')
    details = models.TextField(blank=True, null=True, verbose_name='Детали')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    
    class Meta:
        verbose_name = 'Способ оплаты'
        verbose_name_plural = 'Способы оплаты'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name


class Order(models.Model):
    """
    Заказ
    """
    class PaymentStatus(models.TextChoices):
        PENDING = 'pending', 'Ожидание'
        PAID = 'paid', 'Оплачен'
        FAILED = 'failed', 'Ошибка оплаты'
        CANCELLED = 'cancelled', 'Отменен'
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='orders',
        verbose_name='Пользователь'
    )
    order_number = models.CharField(
        max_length=20,
        unique=True,
        verbose_name='Номер заказа',
        editable=False
    )
    city = models.CharField(max_length=255, verbose_name='Город')
    street = models.CharField(max_length=255, verbose_name='Улица')
    house = models.CharField(max_length=50, verbose_name='Дом')
    apartment = models.CharField(max_length=50, blank=True, null=True, verbose_name='Квартира')
    postal_index = models.CharField(max_length=20, blank=True, null=True, verbose_name='Индекс')
    status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        verbose_name='Статус оплаты'
    )
    delivery_method = models.ForeignKey(
        DeliveryMethod,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders',
        verbose_name='Способ доставки'
    )
    payment_method = models.ForeignKey(
        PaymentMethod,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders',
        verbose_name='Способ оплаты'
    )
    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Общая цена',
        default=0
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    
    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Заказ {self.order_number} - {self.user.get_full_name()}"
    
    def save(self, *args, **kwargs):
        if not self.order_number:
            # Генерируем уникальный номер заказа
            while True:
                order_number = generate_order_number()
                if not Order.objects.filter(order_number=order_number).exists():
                    self.order_number = order_number
                    break
        super().save(*args, **kwargs)


class OrderItem(models.Model):
    """
    Элемент заказа
    """
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Заказ'
    )
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.CASCADE,
        related_name='order_items',
        verbose_name='Продукт'
    )
    quantity = models.PositiveIntegerField(verbose_name='Количество', default=1)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    
    class Meta:
        verbose_name = 'Элемент заказа'
        verbose_name_plural = 'Элементы заказа'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.product.name} x{self.quantity} - {self.order.order_number}"
