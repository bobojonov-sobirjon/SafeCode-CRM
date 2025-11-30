from django.db.models.signals import post_save
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Bills
from apps.v1.notification.models import Notification


def send_notification_to_user(user, message, verb, actor=None, user_object=None, target=None):
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
            target=target,
            category='bills'
        )
        
        # Отправляем через WebSocket
        try:
            channel_layer = get_channel_layer()
            if channel_layer:
                async_to_sync(channel_layer.group_send)(
                    f"user_{user.id}",
                    {
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
                )
        except Exception as e:
            # Если WebSocket недоступен, просто создаем уведомление в БД
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Не удалось отправить уведомление через WebSocket для пользователя {user.id}: {str(e)}")
        
        return notification
    except Exception as e:
        # Логируем ошибку создания уведомления
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Ошибка создания уведомления для пользователя {user.id}: {str(e)}")
        return None


@receiver(post_save, sender=Bills)
def bill_created(sender, instance, created, **kwargs):
    """
    Когда создается Bill, отправляем уведомление пользователю объекта
    """
    if created:
        try:
            user_object = instance.object_id
            bill_creator = instance.user
            object_owner = user_object.user
            
            # Отправляем уведомление только если создатель счета не является владельцем объекта
            if bill_creator != object_owner:
                creator_name = bill_creator.get_full_name() or bill_creator.email
                message = f"Пользователь {creator_name} создал счет для объекта '{user_object.name}'"
                
                # Создаем уведомление с target=Bills для связи
                send_notification_to_user(
                    user=object_owner,
                    message=message,
                    verb="bill_created",
                    actor=bill_creator,
                    user_object=user_object,
                    target=instance  # Связываем с Bills
                )
        except Exception as e:
            # Логируем ошибку, но не прерываем выполнение
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Ошибка в сигнале bill_created: {str(e)}")

