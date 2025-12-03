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
    print(f"[DEBUG] ========== send_notification_to_user called ==========")
    print(f"[DEBUG] User: id={user.id}, email={user.email}")
    print(f"[DEBUG] Message: {message}")
    print(f"[DEBUG] Verb: {verb}")
    print(f"[DEBUG] Actor: {actor.id if actor else None}")
    print(f"[DEBUG] User object: {user_object.id if user_object else None}")
    
    try:
        # Создаем уведомление в БД
        print(f"[DEBUG] Creating notification in database...")
        notification = Notification.objects.create(
            recipient=user,
            actor=actor,
            verb=verb,
            message=message,
            user_object=user_object,
            category='user_object'
        )
        print(f"[DEBUG] Notification created: id={notification.id}")
        
        # Отправляем через WebSocket
        try:
            print(f"[DEBUG] Getting channel layer...")
            channel_layer = get_channel_layer()
            print(f"[DEBUG] Channel layer: {channel_layer}")
            if channel_layer:
                group_name = f"user_{user.id}"
                print(f"[DEBUG] Sending to WebSocket group: {group_name}")
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
                print(f"[DEBUG] Notification data to send: {json.dumps(notification_data, indent=2, ensure_ascii=False)}")
                print(f"[DEBUG] Calling channel_layer.group_send...")
                async_to_sync(channel_layer.group_send)(
                    group_name,
                    notification_data
                )
                print(f"[DEBUG] ========== group_send called successfully for group {group_name} ==========")
            else:
                print(f"[DEBUG] WARNING: Channel layer is None!")
        except Exception as e:
            # Если WebSocket недоступен, просто создаем уведомление в БД
            print(f"[DEBUG] ERROR: Failed to send notification via WebSocket: {str(e)}")
            import traceback
            print(f"[DEBUG] Traceback: {traceback.format_exc()}")
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Не удалось отправить уведомление через WebSocket для пользователя {user.id}: {str(e)}")
        
        return notification
    except Exception as e:
        # Логируем ошибку создания уведомления
        print(f"[DEBUG] ERROR: Failed to create notification: {str(e)}")
        import traceback
        print(f"[DEBUG] Traceback: {traceback.format_exc()}")
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Ошибка создания уведомления для пользователя {user.id}: {str(e)}")
        return None


@receiver(post_save, sender=UserObject)
def user_object_created(sender, instance, created, **kwargs):
    """
    Когда создается UserObject, отправляем уведомление всем администраторам
    """
    print(f"[DEBUG] ========== user_object_created signal triggered ==========")
    print(f"[DEBUG] Created: {created}")
    print(f"[DEBUG] Instance ID: {instance.id}")
    print(f"[DEBUG] Instance name: {instance.name}")
    print(f"[DEBUG] Instance user: id={instance.user.id}, email={instance.user.email}")
    
    if created:
        print(f"[DEBUG] UserObject was created, looking for admin users...")
        # Получаем всех пользователей с ролью "Администратор"
        admin_group = Group.objects.filter(name='Администратор').first()
        print(f"[DEBUG] Admin group: {admin_group}")
        
        if admin_group:
            admin_users = CustomUser.objects.filter(groups=admin_group, is_active=True)
            admin_count = admin_users.count()
            print(f"[DEBUG] Found {admin_count} admin users")
            
            if admin_count > 0:
                creator_name = instance.user.get_full_name() or instance.user.email
                message = f"Новый объект создан пользователем {creator_name}"
                print(f"[DEBUG] Message: {message}")
                
                for admin in admin_users:
                    print(f"[DEBUG] Sending notification to admin: id={admin.id}, email={admin.email}")
                    send_notification_to_user(
                        user=admin,
                        message=message,
                        verb="object_created",
                        actor=instance.user,
                        user_object=instance
                    )
                    print(f"[DEBUG] Notification sent to admin {admin.id}")
            else:
                print(f"[DEBUG] WARNING: No active admin users found!")
        else:
            print(f"[DEBUG] ERROR: Admin group 'Администратор' not found!")
    else:
        print(f"[DEBUG] UserObject was updated, not created. Skipping notification.")
    
    print(f"[DEBUG] ========== user_object_created signal finished ==========")


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
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.error(f"Ошибка отправки уведомления работнику {worker.user.id}: {str(e)}")
            
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
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.error(f"Ошибка отправки уведомления администратору {admin.id}: {str(e)}")
        except Exception as e:
            # Логируем общую ошибку, но не прерываем выполнение
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Ошибка в сигнале user_object_documents_created: {str(e)}")

