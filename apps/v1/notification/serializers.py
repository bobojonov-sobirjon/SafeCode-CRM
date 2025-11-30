from rest_framework import serializers
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    """
    Сериализатор для уведомлений
    """
    actor = serializers.SerializerMethodField()
    user_object = serializers.SerializerMethodField()
    
    class Meta:
        model = Notification
        fields = [
            'id',
            'actor',
            'verb',
            'message',
            'user_object',
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

