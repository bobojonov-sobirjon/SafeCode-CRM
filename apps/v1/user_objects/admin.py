from django.contrib import admin
from .models import UserObject, UserObjectWorkers, UserObjectDocuments, UserObjectDocumentItems


@admin.register(UserObject)
class UserObjectAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'user', 'address', 'status', 'is_deleted', 'created_at']
    list_filter = ['status', 'is_deleted', 'created_at']
    search_fields = ['name', 'address', 'user__email']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']


@admin.register(UserObjectWorkers)
class UserObjectWorkersAdmin(admin.ModelAdmin):
    list_display = ['id', 'user_object', 'user', 'is_finished', 'created_at']
    list_filter = ['is_finished', 'created_at']
    search_fields = ['user_object__name', 'user__email']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']


@admin.register(UserObjectDocuments)
class UserObjectDocumentsAdmin(admin.ModelAdmin):
    list_display = ['id', 'user_object', 'user', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user_object__name', 'user__email']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']


@admin.register(UserObjectDocumentItems)
class UserObjectDocumentItemsAdmin(admin.ModelAdmin):
    list_display = ['id', 'user_object_document', 'document', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user_object_document__user_object__name']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
