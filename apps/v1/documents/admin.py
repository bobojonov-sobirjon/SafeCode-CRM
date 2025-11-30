from django.contrib import admin
from .models import JournalsAndActs, Bills


@admin.register(JournalsAndActs)
class JournalsAndActsAdmin(admin.ModelAdmin):
    list_display = ['id', 'object_id', 'tip', 'date', 'user', 'created_at']
    list_filter = ['tip', 'date', 'created_at']
    search_fields = ['object_id__name', 'user__email', 'tip']
    readonly_fields = ['created_at']
    ordering = ['-created_at']


@admin.register(Bills)
class BillsAdmin(admin.ModelAdmin):
    list_display = ['id', 'object_id', 'price', 'status', 'user', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['object_id__name', 'user__email', 'comment']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
