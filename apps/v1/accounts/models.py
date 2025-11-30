from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import secrets
from apps.v1.website.models import Services

class CustomUser(AbstractUser):
    """
    Custom User model that extends Django's AbstractUser
    """
    email = models.EmailField(
        unique=True,
        verbose_name="Электронная почта",
        help_text="Обязательно. Введите действительный адрес электронной почты."
    )
    phone_number = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        verbose_name="Номер телефона",
        help_text="Необязательно. Введите ваш номер телефона."
    )
    date_of_birth = models.DateField(
        blank=True,
        null=True,
        verbose_name="Дата рождения",
        help_text="Необязательно. Введите вашу дату рождения."
    )
    avatar = models.ImageField(
        upload_to='avatars/',
        blank=True,
        null=True,
        verbose_name="Аватар",
        help_text="Необязательно. Загрузите ваше фото профиля."
    )
    address = models.TextField(
        blank=True,
        null=True,
        verbose_name="Адрес",
        help_text="Необязательно. Введите ваш адрес."
    )
    city = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Город",
        help_text="Необязательно. Введите ваш город."
    )
    street = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Улица",
        help_text="Необязательно. Введите вашу улицу."
    )
    house = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Дом",
        help_text="Необязательно. Введите номер дома."
    )
    apartment = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Квартира",
        help_text="Необязательно. Введите номер квартиры."
    )
    postal_index = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name="Индекс",
        help_text="Необязательно. Введите почтовый индекс."
    )
    email_newsletter = models.BooleanField(
        default=False,
        verbose_name="Email-рассылка",
        help_text="Подписаться на email рассылку."
    )
    special_offers_notifications = models.BooleanField(
        default=False,
        verbose_name="Уведомления о специальных предложениях",
        help_text="Получать уведомления о специальных предложениях."
    )
    id_organization = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="ID организации",
        help_text="Необязательно. Введите ID вашей организации.",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата создания"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Дата обновления"
    )
    reset_token = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Токен сброса пароля",
        help_text="Токен для сброса пароля"
    )
    reset_token_expires = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Время истечения токена"
    )

    # Use email as the username field
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.email} ({self.get_full_name()})"

    def get_full_name(self):
        """
        Return the first_name plus the last_name, with a space in between.
        """
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name if full_name else self.email

    def get_short_name(self):
        """
        Return the short name for the user.
        """
        return self.first_name if self.first_name else self.email


class PurchasedService(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='purchased_services',
        verbose_name='Пользователь'
    )
    service = models.ForeignKey(
        Services,
        on_delete=models.CASCADE,
        related_name='purchases',
        verbose_name='Услуга'
    )
    start_date = models.DateTimeField(
        verbose_name='Дата начала',
        default=timezone.now
    )
    finished_date = models.DateTimeField(
        verbose_name='Дата окончания',
        blank=True,
        null=True
    )
    is_active = models.BooleanField(default=True, verbose_name='Активна')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлено')

    class Meta:
        verbose_name = 'Покупка услуги'
        verbose_name_plural = 'Покупки услуг'
        ordering = ['-created_at']
        unique_together = ('user', 'service', 'start_date')

    def save(self, *args, **kwargs):
        if not self.finished_date and self.start_date:
            self.finished_date = self.start_date + timedelta(days=30)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.service.title}"


class Storage(models.Model):
    """
    Модель хранилища
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='storages',
        verbose_name='Пользователь'
    )
    object = models.ForeignKey(
        'user_objects.UserObject',
        on_delete=models.CASCADE,
        related_name='storages',
        verbose_name='Объект',
        null=True,
        blank=True
    )
    name = models.CharField(
        max_length=255,
        verbose_name='Название',
        help_text='Название хранилища'
    )
    date = models.DateField(
        verbose_name='Дата',
        help_text='Дата хранилища'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )

    class Meta:
        verbose_name = 'Хранилище'
        verbose_name_plural = 'Хранилища'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.user.get_full_name()}"


class StorageFile(models.Model):
    """
    Модель файлов хранилища
    """
    storage = models.ForeignKey(
        Storage,
        on_delete=models.CASCADE,
        related_name='files',
        verbose_name='Хранилище'
    )
    file = models.FileField(
        upload_to='storage/files/',
        verbose_name='Файл',
        help_text='Файл для хранилища'
    )
    name = models.CharField(
        max_length=255,
        verbose_name='Название файла',
        blank=True,
        null=True,
        help_text='Название файла (необязательно)'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )

    class Meta:
        verbose_name = 'Файл хранилища'
        verbose_name_plural = 'Файлы хранилища'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name or self.file.name} - {self.storage.name}"