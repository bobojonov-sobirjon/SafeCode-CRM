from django.db.models.signals import post_save
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Bills, JournalsAndActs
from apps.v1.notification.models import Notification


def send_notification_to_user(user, message, verb, actor=None, user_object=None, target=None, category='bills'):
    """
    Создание уведомления и отправка через WebSocket
    """
    try:
        print(f"[DEBUG] send_notification_to_user called: user_id={user.id if user else None}, message={message}")
        
        # Подготовка target для GenericForeignKey
        target_content_type = None
        target_object_id = None
        if target:
            from django.contrib.contenttypes.models import ContentType
            target_content_type = ContentType.objects.get_for_model(target)
            target_object_id = target.pk
            print(f"[DEBUG] target: {target}, content_type={target_content_type}, object_id={target_object_id}")
        
        # Создаем уведомление в БД
        notification = Notification.objects.create(
            recipient=user,
            actor=actor,
            verb=verb,
            message=message,
            user_object=user_object,
            target_content_type=target_content_type,
            target_object_id=target_object_id,
            category=category
        )
        print(f"[DEBUG] Notification created in DB: id={notification.id}")
        
        # Отправляем через WebSocket
        try:
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
                print(f"[DEBUG] Notification data: {notification_data}")
                async_to_sync(channel_layer.group_send)(
                    group_name,
                    notification_data
                )
                print(f"[DEBUG] WebSocket message sent successfully to group {group_name}")
            else:
                print(f"[DEBUG] WARNING: Channel layer is None!")
        except Exception as e:
            # Если WebSocket недоступен, просто создаем уведомление в БД
            import traceback
            print(f"[ERROR] Не удалось отправить уведомление через WebSocket для пользователя {user.id}: {str(e)}")
            print(f"[ERROR] Traceback: {traceback.format_exc()}")
        
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


@receiver(post_save, sender=JournalsAndActs)
def journal_and_act_created(sender, instance, created, **kwargs):
    """
    Когда создается JournalsAndActs, отправляем уведомление пользователю объекта
    """
    if created:
        try:
            print(f"[DEBUG] journal_and_act_created signal triggered for JournalsAndActs id={instance.id}")
            user_object = instance.object_id
            print(f"[DEBUG] user_object: {user_object}, id={user_object.id if user_object else None}")
            
            journal_creator = instance.user
            print(f"[DEBUG] journal_creator: {journal_creator}, id={journal_creator.id if journal_creator else None}")
            
            object_owner = user_object.user
            print(f"[DEBUG] object_owner: {object_owner}, id={object_owner.id if object_owner else None}")
            
            # Отправляем уведомление владельцу объекта
            creator_name = journal_creator.get_full_name() or journal_creator.email
            type_display = dict(JournalsAndActs.Type.choices).get(instance.type, instance.type or 'Неизвестный тип')
            
            if journal_creator != object_owner:
                message = f"Пользователь {creator_name} создал журнал/акт ({type_display}) для объекта '{user_object.name}'"
            else:
                message = f"Вы создали журнал/акт ({type_display}) для объекта '{user_object.name}'"
            
            print(f"[DEBUG] Sending notification to user_id={object_owner.id}, message={message}")
            
            # Создаем уведомление с target=JournalsAndActs для связи
            notification = send_notification_to_user(
                user=object_owner,
                message=message,
                verb="journal_and_act_created",
                actor=journal_creator,
                user_object=user_object,
                target=instance,  # Связываем с JournalsAndActs
                category='journals_and_acts'
            )
            
            if notification:
                print(f"[DEBUG] Notification created successfully: id={notification.id}")
            else:
                print(f"[DEBUG] ERROR: Notification was not created!")
                
        except Exception as e:
            # Логируем ошибку, но не прерываем выполнение
            import traceback
            print(f"[ERROR] Ошибка в сигнале journal_and_act_created: {str(e)}")
            print(f"[ERROR] Traceback: {traceback.format_exc()}")

