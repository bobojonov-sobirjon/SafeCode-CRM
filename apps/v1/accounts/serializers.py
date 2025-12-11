from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from .models import CustomUser, PurchasedService, Storage, StorageFile
from apps.v1.website.models import Services
from django.utils import timezone
from datetime import timedelta


class RegisterSerializer(serializers.ModelSerializer):
    """
    Сериализатор для регистрации пользователя
    """
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        error_messages={
            'min_length': 'Пароль должен содержать минимум 8 символов.',
            'required': 'Пароль обязателен для заполнения.',
            'blank': 'Пароль не может быть пустым.'
        }
    )
    password_confirm = serializers.CharField(
        write_only=True,
        error_messages={
            'required': 'Подтверждение пароля обязательно.',
            'blank': 'Подтверждение пароля не может быть пустым.'
        }
    )
    groups = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Group.objects.all(),
        required=False,
        error_messages={
            'does_not_exist': 'Группа не существует.',
            'incorrect_type': 'Группа должна быть числом.'
        }
    )
    
    class Meta:
        model = CustomUser
        fields = [
            'first_name', 'last_name', 'id_organization',
            'phone_number', 'email', 'password', 'password_confirm', 'groups'
        ]
        extra_kwargs = {
            'first_name': {
                'error_messages': {
                    'required': 'Имя обязательно для заполнения.',
                    'blank': 'Имя не может быть пустым.'
                }
            },
            'last_name': {
                'error_messages': {
                    'required': 'Фамилия обязательна для заполнения.',
                    'blank': 'Фамилия не может быть пустой.'
                }
            },
            'id_organization': {
                'error_messages': {
                    'required': 'ID организации обязателен для заполнения.',
                    'blank': 'ID организации не может быть пустым.'
                }
            },
            'phone_number': {
                'error_messages': {
                    'required': 'Номер телефона обязателен для заполнения.',
                    'blank': 'Номер телефона не может быть пустым.'
                }
            },
            'email': {
                'error_messages': {
                    'required': 'Email обязателен для заполнения.',
                    'blank': 'Email не может быть пустым.',
                    'invalid': 'Введите корректный email адрес.'
                }
            }
        }

    def validate_email(self, value):
        """
        Проверка уникальности email
        """
        if CustomUser.objects.filter(email=value).exists():
            raise serializers.ValidationError('Пользователь с таким email уже существует.')
        return value

    def validate_phone_number(self, value):
        """
        Проверка уникальности номера телефона
        """
        if CustomUser.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError('Пользователь с таким номером телефона уже существует.')
        return value

    def validate_password(self, value):
        """
        Валидация пароля
        """
        try:
            validate_password(value)
        except ValidationError as e:
            raise serializers.ValidationError(e.messages)
        return value

    def validate(self, attrs):
        """
        Проверка совпадения паролей
        """
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({
                'password_confirm': 'Пароли не совпадают.'
            })
        return attrs

    def create(self, validated_data):
        """
        Создание пользователя
        """
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        
        # Извлекаем groups если он есть
        groups_data = validated_data.pop('groups', None)
        
        # Добавляем username, используя email как username
        if 'username' not in validated_data:
            validated_data['username'] = validated_data.get('email', '')
        
        user = CustomUser.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        
        # Сохраняем группы если они указаны
        if groups_data:
            user.groups.set(groups_data)
        
        return user


class LoginSerializer(serializers.Serializer):
    """
    Сериализатор для входа в систему
    """
    identifier = serializers.CharField(
        error_messages={
            'required': 'Введите номер телефона или email.',
            'blank': 'Поле не может быть пустым.'
        }
    )
    password = serializers.CharField(
        error_messages={
            'required': 'Введите пароль.',
            'blank': 'Пароль не может быть пустым.'
        }
    )

    def validate(self, attrs):
        """
        Проверка учетных данных пользователя
        """
        identifier = attrs.get('identifier')
        password = attrs.get('password')

        # Определяем, является ли поле email или номером телефона
        if '@' in identifier:
            # Это email
            try:
                user = CustomUser.objects.get(email=identifier)
            except CustomUser.DoesNotExist:
                raise serializers.ValidationError({
                    'identifier': 'Пользователь с таким email не найден.'
                })
        else:
            # Это номер телефона
            try:
                user = CustomUser.objects.get(phone_number=identifier)
            except CustomUser.DoesNotExist:
                raise serializers.ValidationError({
                    'identifier': 'Пользователь с таким номером телефона не найден.'
                })

        # Проверяем пароль
        if not user.check_password(password):
            raise serializers.ValidationError({
                'password': 'Неверный пароль.'
            })

        # Проверяем, активен ли пользователь
        if not user.is_active:
            raise serializers.ValidationError({
                'identifier': 'Ваш аккаунт деактивирован. Обратитесь к администратору.'
            })
        
        # Проверяем, подтвержден ли email
        if not user.is_email_verified:
            raise serializers.ValidationError({
                'identifier': 'Ваш email не подтвержден. Пожалуйста, проверьте почту и подтвердите регистрацию по ссылке в письме.'
            })

        attrs['user'] = user
        return attrs


class ProfileSerializer(serializers.ModelSerializer):
    """
    Сериализатор для профиля пользователя
    """
    groups = serializers.SerializerMethodField()
    active_applications = serializers.SerializerMethodField()
    completed_this_month = serializers.SerializerMethodField()
    awaiting_payment = serializers.SerializerMethodField()
    
    class Meta:
        model = CustomUser
        fields = [
            'id', 'first_name', 'last_name', 'email', 'phone_number',
            'id_organization', 'date_of_birth', 'address',
            'city', 'street', 'house', 'apartment', 'postal_index',
            'email_newsletter', 'special_offers_notifications',
            'avatar', 'groups', 'active_applications', 'completed_this_month',
            'awaiting_payment', 'created_at', 'updated_at', 'last_login'
        ]
        read_only_fields = ['id', 'email', 'created_at', 'updated_at', 'last_login', 'active_applications', 'completed_this_month', 'awaiting_payment']
    
    def get_groups(self, obj):
        """
        Получение групп пользователя
        """
        return [{'id': g.id, 'name': g.name} for g in obj.groups.all()]
    
    def get_active_applications(self, obj):
        """
        Получение количества активных заявок
        Активные заявки - это заявки со статусами: active, pending, on_hold
        """
        from apps.v1.user_objects.models import UserObject, UserObjectWorkers
        from django.utils import timezone
        from datetime import datetime
        
        # Проверяем роли пользователя
        is_customer = obj.groups.filter(name='Заказчик').exists()
        is_admin = obj.groups.filter(name='Администратор').exists()
        
        if is_admin:
            # Для Администратора считаем все объекты
            count = UserObject.objects.filter(
                is_deleted=False,
                status__in=[UserObject.Status.ACTIVE, UserObject.Status.PENDING, UserObject.Status.ON_HOLD]
            ).count()
        elif is_customer:
            # Для Заказчика считаем из UserObject
            # Активные заявки: active, pending, on_hold
            count = UserObject.objects.filter(
                user=obj,
                is_deleted=False,
                status__in=[UserObject.Status.ACTIVE, UserObject.Status.PENDING, UserObject.Status.ON_HOLD]
            ).count()
        else:
            # Для других ролей считаем из UserObjectWorkers
            count = UserObjectWorkers.objects.filter(
                user=obj,
                user_object__is_deleted=False,
                user_object__status__in=[UserObject.Status.ACTIVE, UserObject.Status.PENDING, UserObject.Status.ON_HOLD]
            ).count()
        
        return count
    
    def get_completed_this_month(self, obj):
        """
        Получение количества выполненных заявок за текущий месяц
        Выполненные заявки - это заявки со статусами: completed, cancelled
        """
        from apps.v1.user_objects.models import UserObject, UserObjectWorkers
        from django.utils import timezone
        from datetime import datetime
        
        # Получаем текущий месяц и год
        now = timezone.now()
        current_month = now.month
        current_year = now.year
        
        # Проверяем роли пользователя
        is_customer = obj.groups.filter(name='Заказчик').exists()
        is_admin = obj.groups.filter(name='Администратор').exists()
        
        if is_admin:
            # Для Администратора считаем все объекты
            count = UserObject.objects.filter(
                is_deleted=False,
                status__in=[UserObject.Status.COMPLETED, UserObject.Status.CANCELLED],
                updated_at__month=current_month,
                updated_at__year=current_year
            ).count()
        elif is_customer:
            # Для Заказчика считаем из UserObject
            # Выполненные заявки: completed, cancelled
            count = UserObject.objects.filter(
                user=obj,
                is_deleted=False,
                status__in=[UserObject.Status.COMPLETED, UserObject.Status.CANCELLED],
                updated_at__month=current_month,
                updated_at__year=current_year
            ).count()
        else:
            # Для других ролей считаем из UserObjectWorkers
            count = UserObjectWorkers.objects.filter(
                user=obj,
                user_object__is_deleted=False,
                user_object__status__in=[UserObject.Status.COMPLETED, UserObject.Status.CANCELLED],
                user_object__updated_at__month=current_month,
                user_object__updated_at__year=current_year
            ).count()
        
        return count
    
    def get_awaiting_payment(self, obj):
        """
        Получение количества заявок в ожидании оплаты
        """
        # Пока возвращаем 0, логика будет добавлена позже
        return 0
    
    extra_kwargs = {
            'first_name': {
                'error_messages': {
                    'blank': 'Имя не может быть пустым.'
                }
            },
            'last_name': {
                'error_messages': {
                    'blank': 'Фамилия не может быть пустой.'
                }
            },
            'phone_number': {
                'error_messages': {
                    'blank': 'Номер телефона не может быть пустым.'
                }
            }
        }

    def validate_phone_number(self, value):
        """
        Проверка уникальности номера телефона при обновлении
        """
        if self.instance and self.instance.phone_number == value:
            return value
        
        if CustomUser.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError('Пользователь с таким номером телефона уже существует.')
        return value


class ChangePasswordSerializer(serializers.Serializer):
    """
    Сериализатор для смены пароля
    """
    old_password = serializers.CharField(
        error_messages={
            'required': 'Введите текущий пароль.',
            'blank': 'Текущий пароль не может быть пустым.'
        }
    )
    new_password = serializers.CharField(
        min_length=8,
        error_messages={
            'min_length': 'Новый пароль должен содержать минимум 8 символов.',
            'required': 'Новый пароль обязателен для заполнения.',
            'blank': 'Новый пароль не может быть пустым.'
        }
    )
    new_password_confirm = serializers.CharField(
        error_messages={
            'required': 'Подтверждение нового пароля обязательно.',
            'blank': 'Подтверждение нового пароля не может быть пустым.'
        }
    )

    def validate_old_password(self, value):
        """
        Проверка текущего пароля
        """
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Неверный текущий пароль.')
        return value

    def validate_new_password(self, value):
        """
        Валидация нового пароля
        """
        try:
            validate_password(value)
        except ValidationError as e:
            raise serializers.ValidationError(e.messages)
        return value

    def validate(self, attrs):
        """
        Проверка совпадения новых паролей
        """
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({
                'new_password_confirm': 'Новые пароли не совпадают.'
            })
        return attrs


class ForgotPasswordSerializer(serializers.Serializer):
    """
    Сериализатор для восстановления пароля
    """
    email = serializers.EmailField(
        error_messages={
            'required': 'Email обязателен для заполнения.',
            'blank': 'Email не может быть пустым.',
            'invalid': 'Введите корректный email адрес.'
        }
    )

    def validate_email(self, value):
        """
        Проверка существования пользователя с таким email
        """
        # Используем case-insensitive поиск
        if not CustomUser.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('Пользователь с таким email не найден.')
        return value


class ResetPasswordSerializer(serializers.Serializer):
    """
    Сериализатор для сброса пароля с использованием токена
    """
    token = serializers.CharField(
        error_messages={
            'required': 'Токен обязателен для заполнения.',
            'blank': 'Токен не может быть пустым.'
        }
    )
    new_password = serializers.CharField(
        min_length=8,
        error_messages={
            'min_length': 'Новый пароль должен содержать минимум 8 символов.',
            'required': 'Новый пароль обязателен для заполнения.',
            'blank': 'Новый пароль не может быть пустым.'
        }
    )
    new_password_confirm = serializers.CharField(
        error_messages={
            'required': 'Подтверждение нового пароля обязательно.',
            'blank': 'Подтверждение нового пароля не может быть пустым.'
        }
    )

    def validate_new_password(self, value):
        """
        Валидация нового пароля
        """
        try:
            validate_password(value)
        except ValidationError as e:
            raise serializers.ValidationError(e.messages)
        return value

    def validate(self, attrs):
        """
        Проверка совпадения новых паролей
        """
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({
                'new_password_confirm': 'Новые пароли не совпадают.'
            })
        
        # Проверка токена
        token = attrs['token']
        try:
            user = CustomUser.objects.get(reset_token=token)
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError({
                'token': 'Неверный или истекший токен.'
            })
        
        # Проверка истечения токена
        from django.utils import timezone
        if user.reset_token_expires and user.reset_token_expires < timezone.now():
            raise serializers.ValidationError({
                'token': 'Токен истек. Запросите новый.'
            })
        
        attrs['user'] = user
        return attrs


class SimpleChangePasswordSerializer(serializers.Serializer):
    """
    Сериализатор для простой смены пароля (без старого пароля)
    """
    new_password = serializers.CharField(
        min_length=8,
        error_messages={
            'min_length': 'Новый пароль должен содержать минимум 8 символов.',
            'required': 'Новый пароль обязателен для заполнения.',
            'blank': 'Новый пароль не может быть пустым.'
        }
    )
    new_password_confirm = serializers.CharField(
        error_messages={
            'required': 'Подтверждение нового пароля обязательно.',
            'blank': 'Подтверждение нового пароля не может быть пустым.'
        }
    )

    def validate_new_password(self, value):
        """
        Валидация нового пароля
        """
        try:
            validate_password(value)
        except ValidationError as e:
            raise serializers.ValidationError(e.messages)
        return value

    def validate(self, attrs):
        """
        Проверка совпадения новых паролей
        """
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({
                'new_password_confirm': 'Новые пароли не совпадают.'
            })
        return attrs


class UserCreateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для создания пользователя (админ)
    """
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        required=True,
        error_messages={
            'min_length': 'Пароль должен содержать минимум 8 символов.',
            'required': 'Пароль обязателен для заполнения.',
            'blank': 'Пароль не может быть пустым.'
        }
    )
    groups = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Group.objects.all(),
        required=False,
        error_messages={
            'does_not_exist': 'Группа не существует.',
            'incorrect_type': 'Группа должна быть числом.'
        }
    )
    
    class Meta:
        model = CustomUser
        fields = [
            'first_name', 'last_name', 'email', 'phone_number',
            'password', 'groups'
        ]
        extra_kwargs = {
            'first_name': {
                'required': True,
                'error_messages': {
                    'required': 'Имя обязательно для заполнения.',
                    'blank': 'Имя не может быть пустым.'
                }
            },
            'last_name': {
                'required': True,
                'error_messages': {
                    'required': 'Фамилия обязательна для заполнения.',
                    'blank': 'Фамилия не может быть пустой.'
                }
            },
            'email': {
                'required': True,
                'error_messages': {
                    'required': 'Email обязателен для заполнения.',
                    'blank': 'Email не может быть пустым.',
                    'invalid': 'Введите корректный email адрес.'
                }
            },
            'phone_number': {
                'required': True,
                'error_messages': {
                    'required': 'Номер телефона обязателен для заполнения.',
                    'blank': 'Номер телефона не может быть пустым.'
                }
            }
        }

    def validate_email(self, value):
        """
        Проверка уникальности email
        """
        if CustomUser.objects.filter(email=value).exists():
            raise serializers.ValidationError('Пользователь с таким email уже существует.')
        return value

    def validate_phone_number(self, value):
        """
        Проверка уникальности номера телефона
        """
        if CustomUser.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError('Пользователь с таким номером телефона уже существует.')
        return value

    def validate_password(self, value):
        """
        Валидация пароля
        """
        try:
            validate_password(value)
        except ValidationError as e:
            raise serializers.ValidationError(e.messages)
        return value

    def create(self, validated_data):
        """
        Создание пользователя
        """
        password = validated_data.pop('password')
        groups_data = validated_data.pop('groups', None)
        
        # Добавляем username, используя email как username
        if 'username' not in validated_data:
            validated_data['username'] = validated_data.get('email', '')
        
        user = CustomUser.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        
        # Сохраняем группы если они указаны
        if groups_data:
            user.groups.set(groups_data)
        
        return user


class UserListSerializer(serializers.ModelSerializer):
    """
    Сериализатор для списка пользователей
    """
    groups = serializers.SerializerMethodField()
    
    class Meta:
        model = CustomUser
        fields = [
            'id', 'first_name', 'last_name', 'email', 'phone_number',
            'created_at', 'last_login', 'groups'
        ]
        read_only_fields = ['id', 'created_at', 'last_login']
    
    def get_groups(self, obj):
        """
        Получение групп пользователя
        """
        return [{'id': g.id, 'name': g.name} for g in obj.groups.all()]


class PurchasedServiceSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    service = serializers.PrimaryKeyRelatedField(queryset=Services.objects.all())

    class Meta:
        model = PurchasedService
        fields = ['id', 'user', 'service', 'start_date', 'finished_date', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']

    def validate(self, attrs):
        # start_date defaults now if not provided; finished_date 30 days later
        start_date = attrs.get('start_date') or timezone.now()
        finished_date = attrs.get('finished_date') or (start_date + timedelta(days=30))

        if finished_date <= start_date:
            raise serializers.ValidationError({'finished_date': 'Дата окончания должна быть позже даты начала.'})

        attrs['start_date'] = start_date
        attrs['finished_date'] = finished_date
        return attrs
    
    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class PurchasedServiceReadSerializer(serializers.ModelSerializer):
    """
    Сериализатор для чтения PurchasedService с полной информацией о user и service
    """
    user = serializers.SerializerMethodField()
    service = serializers.SerializerMethodField()

    class Meta:
        model = PurchasedService
        fields = ['id', 'user', 'service', 'start_date', 'finished_date', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user', 'service', 'start_date', 'finished_date', 'is_active', 'created_at', 'updated_at']

    def get_user(self, obj):
        """
        Получение информации о пользователе
        """
        if obj.user:
            return {
                'id': obj.user.id,
                'email': obj.user.email,
                'first_name': obj.user.first_name,
                'last_name': obj.user.last_name,
                'phone_number': obj.user.phone_number,
            }
        return None

    def get_service(self, obj):
        """
        Получение информации об услуге
        """
        if obj.service:
            service_data = {
                'id': obj.service.id,
                'title': obj.service.title,
                'description': obj.service.description,
                'price': str(obj.service.price) if obj.service.price else None,
            }
            # Добавляем URL изображения если оно есть
            if obj.service.image:
                request = self.context.get('request')
                if request:
                    service_data['image'] = request.build_absolute_uri(obj.service.image.url)
                else:
                    service_data['image'] = obj.service.image.url
            else:
                service_data['image'] = None
            return service_data
        return None

class LogoutSerializer(serializers.Serializer):
    """
    Сериализатор для выхода из системы
    """
    refresh_token = serializers.CharField(
        required=False,
        allow_blank=True,
        error_messages={
            'blank': 'Refresh токен не может быть пустым.'
        }
    )


class GroupSerializer(serializers.ModelSerializer):
    """
    Сериализатор для групп пользователей
    """
    class Meta:
        model = Group
        fields = ['id', 'name']
        read_only_fields = ['id']


class StorageFileSerializer(serializers.ModelSerializer):
    """
    Сериализатор для файлов хранилища
    """
    class Meta:
        model = StorageFile
        fields = ['id', 'file', 'name', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class StorageFileCreateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для создания файлов хранилища
    """
    class Meta:
        model = StorageFile
        fields = ['file', 'name']
        extra_kwargs = {
            'name': {'required': False, 'allow_blank': True, 'allow_null': True}
        }


class StorageSerializer(serializers.ModelSerializer):
    """
    Сериализатор для чтения хранилища
    """
    files = StorageFileSerializer(many=True, read_only=True)
    object = serializers.SerializerMethodField()
    
    class Meta:
        model = Storage
        fields = ['id', 'object', 'name', 'date', 'files', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at', 'files']
    
    def get_object(self, obj):
        """
        Получение информации об объекте
        """
        if obj.object:
            return {
                'id': obj.object.id,
                'name': obj.object.name,
            }
        return None


class StorageCreateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для создания хранилища
    """
    object_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        write_only=True,
        help_text='ID объекта (необязательно)'
    )
    
    class Meta:
        model = Storage
        fields = ['object_id', 'name', 'date']
        extra_kwargs = {
            'name': {'required': True},
            'date': {'required': True}
        }
        
    def create(self, validated_data):
        """
        Создание хранилища
        """
        object_id = validated_data.pop('object_id', None)
        user = self.context['request'].user
        validated_data['user'] = user
        
        # Устанавливаем object если object_id передан
        if object_id:
            from apps.v1.user_objects.models import UserObject
            try:
                validated_data['object'] = UserObject.objects.get(id=object_id)
            except UserObject.DoesNotExist:
                validated_data['object'] = None
        
        return super().create(validated_data)


class StorageUpdateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для обновления хранилища
    """
    class Meta:
        model = Storage
        fields = ['object', 'name', 'date']
        extra_kwargs = {
            'object': {'required': False, 'allow_null': True}
        }


class AdminPasswordRequestSerializer(serializers.Serializer):
    """
    Сериализатор для запроса SMS кода администратором
    """
    pass  # Не требует полей, использует текущего авторизованного пользователя (админа)


class AdminPasswordVerifySerializer(serializers.Serializer):
    """
    Сериализатор для верификации SMS кода и получения пароля пользователя
    """
    sms_code = serializers.CharField(
        max_length=6,
        min_length=6,
        error_messages={
            'required': 'SMS код обязателен для заполнения.',
            'blank': 'SMS код не может быть пустым.',
            'max_length': 'SMS код должен содержать 6 символов.',
            'min_length': 'SMS код должен содержать 6 символов.'
        }
    )
    user_id = serializers.IntegerField(
        error_messages={
            'required': 'ID пользователя обязателен для заполнения.',
            'invalid': 'ID пользователя должен быть числом.'
        }
    )

    def validate_user_id(self, value):
        """
        Проверка существования пользователя
        """
        try:
            user = CustomUser.objects.get(id=value)
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError('Пользователь с таким ID не найден.')
        return value

    def validate(self, attrs):
        """
        Проверка существования пользователя
        SMS код проверяется в view, так как нужен доступ к request.user (admin)
        """
        user_id = attrs.get('user_id')
        
        try:
            user = CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError({
                'user_id': 'Пользователь с таким ID не найден.'
            })
        
        attrs['user'] = user
        return attrs


class UserDetailSerializer(serializers.ModelSerializer):
    """
    Сериализатор для детальной информации о пользователе (без пароля)
    """
    groups = serializers.SerializerMethodField()
    
    class Meta:
        model = CustomUser
        fields = [
            'id', 'first_name', 'last_name', 'email', 'phone_number',
            'id_organization', 'date_of_birth', 'address',
            'city', 'street', 'house', 'apartment', 'postal_index',
            'email_newsletter', 'special_offers_notifications',
            'avatar', 'groups', 'created_at', 'updated_at', 'last_login',
            'is_active', 'is_staff', 'is_superuser'
        ]
        read_only_fields = ['id', 'email', 'created_at', 'updated_at', 'last_login']
    
    def get_groups(self, obj):
        """
        Получение групп пользователя
        """
        return [{'id': g.id, 'name': g.name} for g in obj.groups.all()]


class UserDetailWithPasswordSerializer(serializers.ModelSerializer):
    """
    Сериализатор для детальной информации о пользователе с паролем
    Faqat kerakli maydonlar qaytariladi: first_name, last_name, email, phone, password
    """
    phone = serializers.CharField(source='phone_number', read_only=True)
    
    class Meta:
        model = CustomUser
        fields = [
            'first_name', 'last_name', 'email', 'phone'
        ]
        read_only_fields = ['first_name', 'last_name', 'email', 'phone']


class UserUpdateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для обновления пользователя
    """
    groups = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Group.objects.all(),
        required=False,
        error_messages={
            'does_not_exist': 'Группа не существует.',
            'incorrect_type': 'Группа должна быть числом.'
        }
    )
    
    class Meta:
        model = CustomUser
        fields = [
            'first_name', 'last_name', 'phone_number',
            'id_organization', 'date_of_birth', 'address',
            'city', 'street', 'house', 'apartment', 'postal_index',
            'email_newsletter', 'special_offers_notifications',
            'avatar', 'groups', 'is_active'
        ]
        extra_kwargs = {
            'first_name': {'required': False},
            'last_name': {'required': False},
            'phone_number': {'required': False},
        }
    
    def validate_phone_number(self, value):
        """
        Проверка уникальности номера телефона (исключая текущего пользователя)
        """
        if value and self.instance:
            if CustomUser.objects.filter(phone_number=value).exclude(id=self.instance.id).exists():
                raise serializers.ValidationError('Пользователь с таким номером телефона уже существует.')
        return value
    
    def update(self, instance, validated_data):
        """
        Обновление пользователя
        """
        groups_data = validated_data.pop('groups', None)
        
        # Обновляем поля
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        
        # Обновляем группы если они указаны
        if groups_data is not None:
            instance.groups.set(groups_data)
        
        return instance


class UserPasswordUpdateSerializer(serializers.Serializer):
    """
    Сериализатор для обновления пароля пользователя
    """
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        required=True,
        error_messages={
            'min_length': 'Пароль должен содержать минимум 8 символов.',
            'required': 'Пароль обязателен для заполнения.',
            'blank': 'Пароль не может быть пустым.'
        }
    )
    
    def validate_password(self, value):
        """
        Валидация пароля
        """
        try:
            validate_password(value)
        except ValidationError as e:
            raise serializers.ValidationError(e.messages)
        return value
    