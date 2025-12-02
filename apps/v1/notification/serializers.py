from rest_framework import serializers
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    """
    Сериализатор для уведомлений
    """
    actor = serializers.SerializerMethodField()
    user_object = serializers.SerializerMethodField()
    target = serializers.SerializerMethodField()
    
    class Meta:
        model = Notification
        fields = [
            'id',
            'actor',
            'verb',
            'message',
            'user_object',
            'target',
            'category',
            'is_read',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_actor(self, obj):
        """
        Получение информации об инициаторе
        """
        if obj.actor:
            return {
                'id': obj.actor.id,
                'first_name': obj.actor.first_name,
                'last_name': obj.actor.last_name,
                'email': obj.actor.email,
            }
        return None
    
    def get_user_object(self, obj):
        """
        Получение информации об объекте пользователя
        """
        if obj.user_object:
            return {
                'id': obj.user_object.id,
                'name': obj.user_object.name,
            }
        return None
    
    def get_target(self, obj):
        """
        Получение информации о связанном объекте (например, Bills, JournalsAndActs)
        """
        if obj.target:
            # Если target - это Bills
            from apps.v1.documents.models import Bills, JournalsAndActs
            if isinstance(obj.target, Bills):
                return {
                    'type': 'bill',
                    'id': obj.target.id,
                    'price': str(obj.target.price) if obj.target.price else None,
                    'status': obj.target.status,
                    'comment': obj.target.comment,
                }
            # Если target - это JournalsAndActs
            elif isinstance(obj.target, JournalsAndActs):
                return {
                    'type': 'journal_and_act',
                    'id': obj.target.id,
                    'type_value': obj.target.type,
                    'date': obj.target.date.isoformat() if obj.target.date else None,
                }
            # Если target - это другой тип объекта
            return {
                'type': obj.target_content_type.model if obj.target_content_type else None,
                'id': obj.target_object_id,
            }
        return None

