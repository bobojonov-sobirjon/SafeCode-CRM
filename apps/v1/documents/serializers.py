from rest_framework import serializers
from .models import JournalsAndActs, Bills
from apps.v1.user_objects.models import UserObject
from apps.v1.accounts.models import CustomUser


class JournalsAndActsSerializer(serializers.ModelSerializer):
    """
    Сериализатор для чтения JournalsAndActs
    """
    object_id = serializers.SerializerMethodField()
    user = serializers.SerializerMethodField()
    
    class Meta:
        model = JournalsAndActs
        fields = [
            'id', 'object_id', 'type', 'date', 'user', 'created_at'
        ]
        read_only_fields = ['id', 'user', 'created_at']
    
    def get_object_id(self, obj):
        """
        Получение информации об объекте
        """
        if obj.object_id:
            return {
                'id': obj.object_id.id,
                'name': obj.object_id.name,
                'address': obj.object_id.address,
            }
        return None
    
    def get_user(self, obj):
        """
        Получение информации о пользователе
        """
        return {
            'id': obj.user.id,
            'email': obj.user.email,
            'first_name': obj.user.first_name,
            'last_name': obj.user.last_name,
        }


class JournalsAndActsCreateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для создания JournalsAndActs
    """
    object_id = serializers.PrimaryKeyRelatedField(
        queryset=UserObject.objects.filter(is_deleted=False),
        error_messages={'does_not_exist': 'Объект не найден или удален.'}
    )
    type = serializers.ChoiceField(
        choices=JournalsAndActs.Type.choices,
        required=False,
        allow_null=True,
        help_text='Тип: estimate (Смета), act (Акт), form (Форма)'
    )
    
    class Meta:
        model = JournalsAndActs
        fields = [
            'object_id', 'type', 'date'
        ]
    
    def create(self, validated_data):
        """
        Создание журнала/акта
        """
        user = self.context['request'].user
        validated_data['user'] = user
        return super().create(validated_data)


class BillsSerializer(serializers.ModelSerializer):
    """
    Сериализатор для чтения Bills
    """
    object_id = serializers.SerializerMethodField()
    user = serializers.SerializerMethodField()
    
    class Meta:
        model = Bills
        fields = [
            'id', 'object_id', 'comment', 'price', 'status', 'user', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']
    
    def get_object_id(self, obj):
        """
        Получение информации об объекте
        """
        if obj.object_id:
            return {
                'id': obj.object_id.id,
                'name': obj.object_id.name,
                'address': obj.object_id.address,
            }
        return None
    
    def get_user(self, obj):
        """
        Получение информации о пользователе
        """
        return {
            'id': obj.user.id,
            'email': obj.user.email,
            'first_name': obj.user.first_name,
            'last_name': obj.user.last_name,
        }


class BillsCreateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для создания Bills
    """
    object_id = serializers.PrimaryKeyRelatedField(
        queryset=UserObject.objects.filter(is_deleted=False),
        error_messages={'does_not_exist': 'Объект не найден или удален.'}
    )
    
    class Meta:
        model = Bills
        fields = [
            'object_id', 'comment', 'price', 'status'
        ]
    
    def create(self, validated_data):
        """
        Создание счета
        """
        user = self.context['request'].user
        validated_data['user'] = user
        return super().create(validated_data)

