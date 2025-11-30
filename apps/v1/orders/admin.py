from django.contrib import admin
from .models import Order, OrderItem, DeliveryMethod, PaymentMethod


@admin.register(DeliveryMethod)
class DeliveryMethodAdmin(admin.ModelAdmin):
    """
    Админка для способов доставки
    """
    list_display = ('name', 'price', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name',)
    ordering = ('-created_at',)


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    """
    Админка для способов оплаты
    """
    list_display = ('name', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name',)
    ordering = ('-created_at',)


class OrderItemInline(admin.TabularInline):
    """
    Инлайн для элементов заказа
    """
    model = OrderItem
    extra = 0
    readonly_fields = ('created_at', 'updated_at')
    fields = ('product', 'quantity', 'created_at')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """
    Админка для заказов
    """
    list_display = ('order_number', 'user', 'status', 'total_price', 'created_at')
    list_filter = ('status', 'created_at', 'delivery_method', 'payment_method')
    search_fields = ('order_number', 'user__email', 'user__first_name', 'user__last_name')
    ordering = ('-created_at',)
    readonly_fields = ('order_number', 'created_at', 'updated_at')
    inlines = [OrderItemInline]
    fieldsets = (
        ('Основная информация', {
            'fields': ('order_number', 'user', 'status')
        }),
        ('Адрес доставки', {
            'fields': ('city', 'street', 'house', 'apartment', 'postal_index')
        }),
        ('Доставка и оплата', {
            'fields': ('delivery_method', 'payment_method', 'total_price')
        }),
        ('Даты', {
            'fields': ('created_at', 'updated_at')
        }),
    )
