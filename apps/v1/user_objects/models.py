from django.db import models
from apps.v1.accounts.models import CustomUser


class UserObject(models.Model):
    class Status(models.TextChoices):
        ACTIVE = 'active', 'Активный'
        PENDING = 'pending', 'Ожидание'
        COMPLETED = 'completed', 'Завершенный'
        CANCELLED = 'cancelled', 'Отмененный'
        ON_HOLD = 'on_hold', 'На паузе'
        
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='user_objects')
    name = models.CharField(max_length=255, verbose_name='Название объекта', null=True, blank=True)
    address = models.CharField(max_length=255, verbose_name='Адрес объекта', null=True, blank=True)
    latitude = models.DecimalField(max_digits=10, decimal_places=8, verbose_name='Широта', null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=8, verbose_name='Долгота', null=True, blank=True)
    size = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Размер', null=True, blank=True)
    number_of_fire_extinguishing_systems = models.IntegerField(verbose_name='Кол-во систем пожаротушения', null=True, blank=True)
    status = models.CharField(max_length=255, verbose_name='Статус объекта', null=True, blank=True, choices=Status.choices, default=Status.ACTIVE)
    is_deleted = models.BooleanField(default=False, verbose_name='Удален')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    
    objects = models.Manager()
    
    class Meta:
        verbose_name = 'Объект пользователя'
        verbose_name_plural = '01. Объекты пользователей'
        ordering = ['-created_at']
        
    def __str__(self):
        return self.name
    

class UserObjectWorkers(models.Model):
    user_object = models.ForeignKey(UserObject, on_delete=models.CASCADE, related_name='user_object_workers')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='user_object_workers')
    is_finished = models.BooleanField(default=False, verbose_name='Завершен')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    
    objects = models.Manager()
    
    class Meta:
        verbose_name = 'Работник объекта пользователя'
        verbose_name_plural = '02. Работники объектов пользователей'


class UserObjectDocuments(models.Model):
    user_object = models.ForeignKey(UserObject, on_delete=models.CASCADE, related_name='user_object_documents')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='user_object_documents')
    comment = models.TextField(verbose_name='Комментарий', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    
    objects = models.Manager()
    
    class Meta:
        verbose_name = 'Документ объекта пользователя'
        verbose_name_plural = '03. Документы объектов пользователей'


class UserObjectDocumentItems(models.Model):
    user_object_document = models.ForeignKey(UserObjectDocuments, on_delete=models.CASCADE, related_name='user_object_document_items')
    document = models.FileField(upload_to='user_objects/documents/', verbose_name='Документ', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    
    objects = models.Manager()
    
    class Meta:
        verbose_name = 'Элемент документа объекта пользователя'
        verbose_name_plural = '04. Элементы документов объектов пользователей'