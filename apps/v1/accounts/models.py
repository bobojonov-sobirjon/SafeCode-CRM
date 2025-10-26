from turtle import position
from django.contrib.auth.models import AbstractUser
from django.db import models
from decimal import Decimal
import secrets

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