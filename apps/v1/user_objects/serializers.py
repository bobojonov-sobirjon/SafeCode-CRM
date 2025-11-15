from rest_framework import serializers
from .models import UserObject, UserObjectWorkers, UserObjectDocuments, UserObjectDocumentItems
from apps.v1.accounts.models import CustomUser


class UserObjectSerializer(serializers.ModelSerializer):
    """
    Сериализатор для чтения UserObject
    """
    user = serializers.SerializerMethodField()
    workers_document = serializers.SerializerMethodField()
    
    class Meta:
        model = UserObject
        fields = [
            'id', 'user', 'name', 'address', 'latitude', 'longitude',
            'size', 'number_of_fire_extinguishing_systems', 'status',
            'is_deleted', 'created_at', 'updated_at', 'workers_document'
        ]
        read_only_fields = ['id', 'user', 'status', 'created_at', 'updated_at', 'is_deleted', 'workers_document']
    
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
    
    def get_workers_document(self, obj):
        """
        Получение данных о работниках и их документах
        """
        from .utils import get_workers_document_data
        request = self.context.get('request')
        return get_workers_document_data(obj, request)


class UserObjectCreateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для создания UserObject
    """
    class Meta:
        model = UserObject
        fields = [
            'name', 'address', 'latitude', 'longitude',
            'size', 'number_of_fire_extinguishing_systems'
        ]
        # status, created_at, updated_at не включаются - они автоматические
    
    def create(self, validated_data):
        """
        Создание объекта пользователя
        """
        user = self.context['request'].user
        validated_data['user'] = user
        # status по умолчанию PENDING
        return super().create(validated_data)


class UserObjectUpdateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для обновления UserObject
    """
    class Meta:
        model = UserObject
        fields = [
            'name', 'address', 'latitude', 'longitude',
            'size', 'number_of_fire_extinguishing_systems', 'status'
        ]


class UserObjectWorkersAddSerializer(serializers.Serializer):
    """
    Сериализатор для добавления работников к объекту
    """
    user_objects_id = serializers.IntegerField(required=True)
    worker_list = serializers.ListField(
        child=serializers.IntegerField(),
        required=True,
        allow_empty=False,
        min_length=1
    )
    
    def validate_user_objects_id(self, value):
        """
        Проверка существования объекта
        """
        if not UserObject.objects.filter(id=value, is_deleted=False).exists():
            raise serializers.ValidationError('Объект не найден или удален.')
        return value
    
    def validate_worker_list(self, value):
        """
        Проверка существования пользователей
        """
        if not value:
            raise serializers.ValidationError('Список работников не может быть пустым.')
        
        # Проверяем существование всех пользователей
        existing_users = CustomUser.objects.filter(id__in=value).values_list('id', flat=True)
        missing_ids = set(value) - set(existing_users)
        
        if missing_ids:
            raise serializers.ValidationError(f'Пользователи с ID {list(missing_ids)} не найдены.')
        
        return value
    
    def create(self, validated_data):
        """
        Добавление работников к объекту
        """
        user_object_id = validated_data['user_objects_id']
        worker_ids = validated_data['worker_list']
        
        # Получаем объект
        user_object = UserObject.objects.get(id=user_object_id)
        
        # Изменяем статус объекта на PENDING
        user_object.status = UserObject.Status.PENDING
        user_object.save()
        
        # Создаем записи для работников
        created_workers = []
        for worker_id in worker_ids:
            # Проверяем, не добавлен ли уже этот работник
            worker, created = UserObjectWorkers.objects.get_or_create(
                user_object=user_object,
                user_id=worker_id,
                defaults={'is_finished': False}
            )
            if created:
                created_workers.append(worker)
        
        return {
            'user_object': user_object,
            'workers': created_workers
        }


class WorkerSerializer(serializers.ModelSerializer):
    """
    Сериализатор для работников
    """
    class Meta:
        model = CustomUser
        fields = ['id', 'first_name', 'last_name', 'email', 'phone_number']
        read_only_fields = ['id']


class UserObjectDocumentCreateSerializer(serializers.Serializer):
    """
    Сериализатор для создания документов объекта
    """
    user_object_id = serializers.IntegerField(required=True)
    comment = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    document_list = serializers.ListField(
        child=serializers.FileField(),
        required=True,
        allow_empty=False,
        min_length=1
    )
    
    def validate_user_object_id(self, value):
        """
        Проверка существования объекта
        """
        if not UserObject.objects.filter(id=value, is_deleted=False).exists():
            raise serializers.ValidationError('Объект не найден или удален.')
        return value
    
    def to_internal_value(self, data):
        """
        Обработка multipart/form-data для загрузки файлов
        """
        # Получаем базовые поля
        internal_value = {
            'user_object_id': data.get('user_object_id'),
            'comment': data.get('comment', ''),
        }
        
        # Обрабатываем файлы
        files = self.context.get('files', {})
        document_list = []
        
        # Получаем все файлы
        # В form-data файлы могут приходить как:
        # - document_list[0], document_list[1], ...
        # - document_list (один файл)
        # - document_list[] (массив)
        for key in files.keys():
            if 'document_list' in key.lower():
                document_list.append(files[key])
        
        # Также проверяем, может быть передан список через data
        if 'document_list' in data:
            if isinstance(data.get('document_list'), list):
                document_list.extend(data.get('document_list'))
            elif data.get('document_list'):
                document_list.append(data.get('document_list'))
        
        if not document_list:
            raise serializers.ValidationError({'document_list': 'Необходимо загрузить хотя бы один документ.'})
        
        internal_value['document_list'] = document_list
        return internal_value
    
    def create(self, validated_data):
        """
        Создание документа и его элементов
        """
        user = self.context['request'].user
        user_object_id = validated_data['user_object_id']
        comment = validated_data.get('comment', '')
        document_list = validated_data['document_list']
        
        # Получаем объект
        user_object = UserObject.objects.get(id=user_object_id)
        
        # Создаем документ
        user_object_document = UserObjectDocuments.objects.create(
            user_object=user_object,
            user=user,
            comment=comment
        )
        
        # Создаем элементы документа
        document_items = []
        for document_file in document_list:
            item = UserObjectDocumentItems.objects.create(
                user_object_document=user_object_document,
                document=document_file
            )
            document_items.append(item)
        
        # Если пользователь с ролью "Менеджер" создал документ, меняем статус объекта на COMPLETED
        if user.groups.filter(name='Менеджер').exists():
            user_object.status = UserObject.Status.COMPLETED
            user_object.save()
        
        return {
            'user_object_document': user_object_document,
            'document_items': document_items
        }

