from django.shortcuts import render
from django.utils import timezone
from datetime import timedelta
from django.core.mail import send_mail
from django.conf import settings
from celery import shared_task
from apps.v1.notification.models import Notification
from apps.v1.accounts.models import PurchasedService, CustomUser


@shared_task
def notify_expiring_services():
    now = timezone.now()
    for days_left in [10, 7, 4, 1]:
        target_date = now + timedelta(days=days_left)
        purchases = PurchasedService.objects.filter(is_active=True, finished_date__date=target_date.date())
        for purchase in purchases.select_related('user', 'service'):
            # In-app notification
            Notification.objects.create(
                recipient=purchase.user,
                actor=None,
                verb='service_expiry_reminder',
                message=f"Услуга '{purchase.service.title}' истекает через {days_left} дней. Пожалуйста, продлите.",
                target=purchase,
                category='service'
            )
            # Email
            try:
                send_mail(
                    'Напоминание: срок услуги истекает',
                    f"Здравствуйте, {purchase.user.get_full_name()}!\n\nУслуга '{purchase.service.title}' истекает через {days_left} дней. Пожалуйста, проверьте и продлите при необходимости.",
                    settings.DEFAULT_FROM_EMAIL,
                    [purchase.user.email],
                    fail_silently=True,
                )
            except Exception:
                pass


# Create your views here.
