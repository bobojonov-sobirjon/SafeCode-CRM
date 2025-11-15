from django.contrib import admin

from apps.v1.products.models import Product, ProductImage, ProductSizes, Category


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ('image',)
    readonly_fields = ('created_at', 'updated_at')
    verbose_name = "Изображение продукта"
    verbose_name_plural = "Изображения продукта"
    ordering = ['-created_at']


class ProductSizesInline(admin.TabularInline):
    model = ProductSizes
    extra = 1
    fields = ('width', 'height', 'depth',)
    readonly_fields = ('created_at', 'updated_at')
    verbose_name = "Характеристика продукта"
    verbose_name_plural = "Характеристики продукта"
    ordering = ['-created_at']


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')
    fields = ('name', 'description')
    verbose_name = "Категория"
    verbose_name_plural = "01. Категории"
    


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'article', 'stock', 'is_active', 'is_deleted', 'created_at', 'updated_at')
    list_filter = ('is_active', 'is_deleted', 'created_at', 'updated_at')
    search_fields = ('name', 'article')
    inlines = [ProductImageInline, ProductSizesInline]
    readonly_fields = ('created_at', 'updated_at')
    fields = ('name', 'description', 'price', 'article', 'category', 'stock', 'is_active', 'is_deleted')
    verbose_name = "Продукт"
    verbose_name_plural = "01. Продукты"
    ordering = ['-created_at']