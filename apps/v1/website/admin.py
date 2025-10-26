from django.contrib import admin
from apps.v1.website.models import Services, ServiceItems, Contacts
from django.utils.html import mark_safe
from import_export import resources
from import_export.admin import ImportExportModelAdmin


class ServiceItemsResource(resources.ModelResource):
    class Meta:
        model = ServiceItems
        fields = ('id', 'service', 'content', 'created_at', 'updated_at')
        export_order = ('id', 'service', 'content', 'created_at', 'updated_at')


class ServicesResource(resources.ModelResource):
    class Meta:
        model = Services
        fields = ('id', 'title', 'image', 'description', 'why_this_service', 'for_whom', 'price', 'created_at', 'updated_at')
        export_order = ('id', 'title', 'image', 'description', 'why_this_service', 'for_whom', 'price', 'created_at', 'updated_at')


class ServiceItemsInline(admin.TabularInline):
    model = ServiceItems
    extra = 1
    fields = ('content',)
    show_change_link = True
    readonly_fields = ('created_at', 'updated_at')
    can_delete = True
    verbose_name = "Включает в себя"
    verbose_name_plural = "Включает в себя"
    ordering = ['-created_at']
    

class ServicesAdmin(ImportExportModelAdmin):
    resource_class = ServicesResource
    
    def image_tag(self, obj):
        return mark_safe(f'<img src="{obj.image.url}" style="width: 100px; height: 100px;" />')
    image_tag.short_description = 'Изображение'
    
    list_display = ('image_tag', 'title', 'description', 'why_this_service', 'for_whom', 'price', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('title', 'description', 'why_this_service', 'for_whom', 'price')
    inlines = [ServiceItemsInline]
    readonly_fields = ('created_at', 'updated_at')
    fields = ('title', 'image', 'description', 'why_this_service', 'for_whom', 'price')
    verbose_name = "Услуга"
    verbose_name_plural = "Услуги"
    ordering = ['-created_at']

class ServiceItemsAdmin(ImportExportModelAdmin):
    resource_class = ServiceItemsResource
    
    list_display = ('service', 'content', 'created_at', 'updated_at')
    list_filter = ('service', 'created_at', 'updated_at')
    search_fields = ('service__title', 'content')
    readonly_fields = ('created_at', 'updated_at')
    fields = ('service', 'content')
    verbose_name = "Элемент услуги"
    verbose_name_plural = "Элементы услуг"
    ordering = ['-created_at']


class ContactsResource(resources.ModelResource):
    class Meta:
        model = Contacts
        fields = ('id', 'address', 'phone', 'email', 'working_hours_mon_thu', 'working_hours_fri', 'working_hours_sat_sun', 'map_iframe', 'created_at', 'updated_at')
        export_order = ('id', 'address', 'phone', 'email', 'working_hours_mon_thu', 'working_hours_fri', 'working_hours_sat_sun', 'map_iframe', 'created_at', 'updated_at')


class ContactsAdmin(ImportExportModelAdmin):
    resource_class = ContactsResource
    
    list_display = ('address', 'phone', 'email', 'working_hours_mon_thu', 'working_hours_fri', 'working_hours_sat_sun', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('address', 'phone', 'email')
    readonly_fields = ('created_at', 'updated_at')
    fields = ('address', 'phone', 'email', 'working_hours_mon_thu', 'working_hours_fri', 'working_hours_sat_sun', 'map_iframe')
    verbose_name = "Контакты"
    verbose_name_plural = "Контакты"
    ordering = ['-created_at']


admin.site.register(Services, ServicesAdmin)
admin.site.register(ServiceItems, ServiceItemsAdmin)
admin.site.register(Contacts, ContactsAdmin)