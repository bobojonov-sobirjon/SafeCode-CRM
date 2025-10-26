from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from .models import CustomUser


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

        attrs['user'] = user
        return attrs


class ProfileSerializer(serializers.ModelSerializer):
    """
    Сериализатор для профиля пользователя
    """
    groups = serializers.SerializerMethodField()
    
    class Meta:
        model = CustomUser
        fields = [
            'id', 'first_name', 'last_name', 'email', 'phone_number',
            'id_organization', 'date_of_birth', 'address',
            'city', 'street', 'house', 'apartment', 'postal_index',
            'email_newsletter', 'special_offers_notifications',
            'avatar', 'groups', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'email', 'created_at', 'updated_at']
    
    def get_groups(self, obj):
        """
        Получение групп пользователя
        """
        return [{'id': g.id, 'name': g.name} for g in obj.groups.all()]
    
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
