from django.db import models

class Services(models.Model):
    title = models.CharField(max_length=255, blank=True, null=True, verbose_name="Название услуги")
    image = models.ImageField(upload_to='services/', blank=True, null=True, verbose_name="Изображение услуги")
    description = models.TextField(blank=True, null=True, verbose_name="Описание услуги")
    why_this_service = models.TextField(blank=True, null=True, verbose_name="Почему эта услуга")
    for_whom = models.TextField(blank=True, null=True, verbose_name="Для кого эта услуга")
    price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name="Цена")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    
    class Meta:
        verbose_name = "Услуга"
        verbose_name_plural = "01. Услуги"
        ordering = ['-created_at']
        
    def __str__(self):
        return self.title


class ServiceItems(models.Model):
    service = models.ForeignKey(Services, on_delete=models.CASCADE, verbose_name="Услуга")
    content = models.TextField(blank=True, null=True, verbose_name="Контент элемента")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    
    class Meta:
        verbose_name = "Элемент услуги"
        verbose_name_plural = "02. Элементы услуг"
        ordering = ['-created_at']
        
    def __str__(self):
        return self.service.title
    

class Contacts(models.Model):
    address = models.CharField(max_length=500, blank=True, null=True, verbose_name="Адрес")
    phone = models.CharField(max_length=50, blank=True, null=True, verbose_name="Телефон")
    email = models.EmailField(blank=True, null=True, verbose_name="E-mail")
    working_hours_mon_thu = models.CharField(max_length=100, blank=True, null=True, verbose_name="Режим работы Пн-Чт")
    working_hours_fri = models.CharField(max_length=100, blank=True, null=True, verbose_name="Режим работы Пт")
    working_hours_sat_sun = models.CharField(max_length=100, blank=True, null=True, verbose_name="Режим работы Сб-Вс")
    map_iframe = models.TextField(blank=True, null=True, verbose_name="Карта (iframe)")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    
    class Meta:
        verbose_name = "Контакты"
        verbose_name_plural = "03. Контакты"
        ordering = ['-created_at']
        
    def __str__(self):
        return f"Контакты - {self.address}"
        