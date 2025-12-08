from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import Group
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import UserObject, UserObjectWorkers, UserObjectDocuments
from apps.v1.accounts.models import CustomUser
from apps.v1.notification.models import Notification
import json


def send_notification_to_user(user, message, verb, actor=None, user_object=None):
    """
    Создание уведомления и отправка через WebSocket
    """
    try:
        # Создаем уведомление в БД
        notification = Notification.objects.create(
            recipient=user,
            actor=actor,
            verb=verb,
            message=message,
            user_object=user_object,
            category='user_object'
        )
        
        # Отправляем через WebSocket
        try:
            channel_layer = get_channel_layer()
            if channel_layer:
                group_name = f"user_{user.id}"
                notification_data = {
                    "type": "notification_message",
                    "notification": {
                        "id": notification.id,
                        "message": message,
                        "verb": verb,
                        "actor": {
                            "id": actor.id,
                            "first_name": actor.first_name,
                            "last_name": actor.last_name,
                        } if actor else None,
                        "user_object": {
                            "id": user_object.id,
                            "name": user_object.name,
                        } if user_object else None,
                        "created_at": notification.created_at.isoformat(),
                        "is_read": notification.is_read,
                    }
                }
                async_to_sync(channel_layer.group_send)(
                    group_name,
                    notification_data
                )
        except Exception as e:
            # Если WebSocket недоступен, просто создаем уведомление в БД
            pass
        
        return notification
    except Exception as e:
        return None


@receiver(post_save, sender=UserObject)
def user_object_created(sender, instance, created, **kwargs):
    """
    Когда создается UserObject, отправляем уведомление всем администраторам
    """
    if created:
        # Получаем всех пользователей с ролью "Администратор"
        admin_group = Group.objects.filter(name='Администратор').first()
        
        if admin_group:
            admin_users = CustomUser.objects.filter(groups=admin_group, is_active=True)
            
            if admin_users.exists():
                creator_name = instance.user.get_full_name() or instance.user.email
                message = f"Новый объект создан пользователем {creator_name}"
                
                for admin in admin_users:
                    send_notification_to_user(
                        user=admin,
                        message=message,
                        verb="object_created",
                        actor=instance.user,
                        user_object=instance
                    )


@receiver(post_save, sender=UserObjectWorkers)
def user_object_workers_created(sender, instance, created, **kwargs):
    """
    Когда создается UserObjectWorkers:
    1. Отправляем уведомление выбранным работникам
    Примечание: Уведомление создателю объекта отправляется из serializer после добавления всех работников
    """
    if created:
        user_object = instance.user_object
        worker = instance.user
        
        # Уведомление работнику
        message_to_worker = f"Объект '{user_object.name}' отправлен администратором для проверки"
        send_notification_to_user(
            user=worker,
            message=message_to_worker,
            verb="object_assigned",
            actor=user_object.user,  # Создатель объекта
            user_object=user_object
        )


@receiver(post_save, sender=UserObjectDocuments)
def user_object_documents_created(sender, instance, created, **kwargs):
    """
    Когда создается UserObjectDocuments:
    1. Отправляем уведомление другим работникам этого объекта (кроме создателя документа)
    2. Отправляем уведомление всем администраторам
    3. Устанавливаем is_finished=True для UserObjectWorkers этого пользователя
    """
    if created:
        try:
            user_object = instance.user_object
            document_creator = instance.user
            
            # Устанавливаем is_finished=True для UserObjectWorkers
            UserObjectWorkers.objects.filter(
                user_object=user_object,
                user=document_creator
            ).update(is_finished=True)
            
            # Получаем роль создателя документа
            creator_groups = document_creator.groups.all()
            creator_role = None
            for group in creator_groups:
                if group.name not in ['Администратор', 'Заказчик']:
                    creator_role = group.name
                    break
            
            creator_name = document_creator.get_full_name() or document_creator.email
            role_text = f"с ролью {creator_role}" if creator_role else ""
            
            # 1. Уведомление другим работникам этого объекта
            workers = UserObjectWorkers.objects.filter(user_object=user_object).exclude(user=document_creator)
            if workers.exists():
                for worker in workers:
                    try:
                        message = f"Пользователь {creator_name} {role_text} проверил объект '{user_object.name}' и загрузил документы"
                        send_notification_to_user(
                            user=worker.user,
                            message=message,
                            verb="object_documents_uploaded",
                            actor=document_creator,
                            user_object=user_object
                        )
                    except Exception as e:
                        # Логируем ошибку, но продолжаем работу
                        pass
            
            # 2. Уведомление всем администраторам (всегда отправляем)
            admin_group = Group.objects.filter(name='Администратор').first()
            if admin_group:
                admin_users = CustomUser.objects.filter(groups=admin_group, is_active=True)
                message = f"Пользователь {creator_name} {role_text} проверил объект '{user_object.name}' и загрузил документы"
                for admin in admin_users:
                    try:
                        send_notification_to_user(
                            user=admin,
                            message=message,
                            verb="object_documents_uploaded",
                            actor=document_creator,
                            user_object=user_object
                        )
                    except Exception as e:
                        # Логируем ошибку, но продолжаем работу
                        pass
        except Exception as e:
            # Логируем общую ошибку, но не прерываем выполнение
            pass

