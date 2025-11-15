from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.sites.models import Site
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
from .models import CustomUser

# Unregister Token Blacklist models
try:
    admin.site.unregister(OutstandingToken)
except admin.sites.NotRegistered:
    pass

try:
    admin.site.unregister(BlacklistedToken)
except admin.sites.NotRegistered:
    pass

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """
    Настройка админки для пользователей
    """
    list_display = ('email', 'username', 'first_name', 'last_name', 'get_groups', 'is_staff', 'is_active', 'created_at')
    list_filter = ('is_staff', 'is_superuser', 'groups', 'is_active', 'created_at')
    search_fields = ('email', 'username', 'first_name', 'last_name', 'phone_number')
    ordering = ('-created_at',)
    
    def get_groups(self, obj):
        """
        Получение списка групп пользователя
        """
        return ", ".join([group.name for group in obj.groups.all()])
    get_groups.short_description = 'Группы'
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Личная информация', {'fields': ('first_name', 'last_name', 'email', 'phone_number', 'date_of_birth', 'avatar', 'address')}),
        ('Адрес', {'fields': ('city', 'street', 'house', 'apartment', 'postal_index')}),
        ('Уведомления', {'fields': ('email_newsletter', 'special_offers_notifications')}),
        ('Права доступа', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups')}),
        ('Важные даты', {'fields': ('last_login', 'date_joined', 'created_at', 'updated_at')}),
        ('Организация', {'fields': ('id_organization',)}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'first_name', 'last_name', 'password1', 'password2'),
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at', 'date_joined', 'last_login', 'reset_token', 'reset_token_expires')
    

admin.site.unregister(Site)

admin.site.site_header = "SafeCode CRM Admin"
admin.site.site_title = "SafeCode CRM Admin"
admin.site.index_title = "Welcome to SafeCode CRM Admin"