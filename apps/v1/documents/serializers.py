from rest_framework import serializers
from .models import JournalsAndActs, Bills, JournalAndActDocuments, BillDocuments
from apps.v1.user_objects.models import UserObject
from apps.v1.accounts.models import CustomUser
from .mixins import FileValidationMixin


class JournalsAndActsDocumentSerializer(serializers.ModelSerializer):
    """
    Сериализатор для чтения JournalAndActDocuments
    """
    document = serializers.SerializerMethodField()
    
    class Meta:
        model = JournalAndActDocuments
        fields = ['id', 'document']
        read_only_fields = ['id']
    
    def get_document(self, obj):
        """
        Получение URL документа
        """
        request = self.context.get('request')
        if obj.document and hasattr(obj.document, 'url'):
            if request:
                return request.build_absolute_uri(obj.document.url)
            return obj.document.url
        return None
        

class JournalsAndActsSerializer(serializers.ModelSerializer):
    """
    Сериализатор для чтения JournalsAndActs
    """
    object_id = serializers.SerializerMethodField()
    user = serializers.SerializerMethodField()
    document_list = serializers.SerializerMethodField()
    
    class Meta:
        model = JournalsAndActs
        fields = [
            'id', 'object_id', 'type', 'date', 'user', 'created_at', 'document_list'
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

    def get_document_list(self, obj):
        """
        Получение информации о документах
        """
        documents = obj.journal_and_act_documents.all()
        serializer = JournalsAndActsDocumentSerializer(documents, many=True, context=self.context)
        return serializer.data


class JournalsAndActsCreateSerializer(FileValidationMixin, serializers.Serializer):
    """
    Сериализатор для создания JournalsAndActs с документами
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
    date = serializers.DateField(required=False, allow_null=True)
    document_list = serializers.ListField(
        child=serializers.FileField(),
        required=False,
        allow_empty=True
    )
    
    def to_internal_value(self, data):
        """
        Обработка multipart/form-data для загрузки файлов
        """
        # Получаем object_id и конвертируем в UserObject instance
        object_id_value = data.get('object_id')
        user_object = None
        if object_id_value:
            try:
                object_id = int(object_id_value)
                user_object = UserObject.objects.filter(id=object_id, is_deleted=False).first()
                if not user_object:
                    raise serializers.ValidationError({'object_id': 'Объект не найден или удален.'})
            except (ValueError, TypeError):
                raise serializers.ValidationError({'object_id': 'Неверный формат ID объекта.'})
        else:
            raise serializers.ValidationError({'object_id': 'Это поле обязательно.'})
        
        internal_value = {
            'object_id': user_object,  # UserObject instance
            'type': data.get('type'),
            'date': data.get('date'),
        }
        
        # Обрабатываем файлы - для multipart/form-data файлы всегда в request.FILES
        files = self.context.get('files', {})
        document_list = []
        
        # Получаем все файлы из request.FILES
        # В form-data файлы могут приходить как:
        # - document_list[0], document_list[1], ... (несколько файлов с индексами)
        # - document_list (один файл или несколько файлов с одним ключом)
        # - document_list[] (массив, один файл)
        
        # Сначала проверяем, есть ли файлы с ключами document_list[0], document_list[1] и т.д.
        document_keys = [key for key in files.keys() if key.startswith('document_list[')]
        if document_keys:
            # Если есть файлы с индексами, сортируем их и добавляем
            document_keys.sort(key=lambda x: int(x.split('[')[1].split(']')[0]) if '[' in x and ']' in x else 0)
            for key in document_keys:
                document_list.append(files[key])
        else:
            # Если нет файлов с индексами, ищем document_list
            # Django'da bir xil key bilan bir nechta fayl yuborilganda, ular list sifatida keladi
            request = self.context.get('request')
            if request and hasattr(request, 'FILES'):
                # getlist() orqali barcha fayllarni olamiz
                document_list = request.FILES.getlist('document_list')
                # Agar getlist() bo'sh bo'lsa, oddiy key bilan qidiramiz
                if not document_list:
                    if 'document_list' in files:
                        # Agar bir fayl bo'lsa, uni list ga aylantiramiz
                        document_list = [files['document_list']]
                    elif 'document_list[]' in files:
                        document_list = [files['document_list[]']]
            else:
                # Agar request yo'q bo'lsa, oddiy files dict dan olamiz
                if 'document_list' in files:
                    # Django'da bir xil key bilan bir nechta fayl yuborilganda, ular list sifatida keladi
                    if isinstance(files['document_list'], list):
                        document_list = files['document_list']
                    else:
                        document_list = [files['document_list']]
                elif 'document_list[]' in files:
                    if isinstance(files['document_list[]'], list):
                        document_list = files['document_list[]']
                    else:
                        document_list = [files['document_list[]']]
        
        # Fayllarni validatsiya qilish
        if document_list:
            self.validate_files(document_list)
        
        internal_value['document_list'] = document_list
        return internal_value
    
    def validate(self, attrs):
        """
        Fayllarni validatsiya qilish
        """
        document_list = attrs.get('document_list', [])
        if document_list:
            self.validate_files(document_list)
        return attrs
    
    def create(self, validated_data):
        """
        Создание журнала/акта с документами
        Bulk operations ishlatilmoqda - tezroq ishlash uchun
        """
        user = self.context['request'].user
        object_id = validated_data['object_id']
        type_value = validated_data.get('type')
        date_value = validated_data.get('date')
        document_list = validated_data.get('document_list', [])
        
        # Создаем журнал/акт
        journal_and_act = JournalsAndActs.objects.create(
            object_id=object_id,
            user=user,
            type=type_value,
            date=date_value
        )
        
        # Bulk create ishlatilmoqda - tezroq ishlash uchun
        if document_list:
            documents = [
                JournalAndActDocuments(
                    journal_and_act_id=journal_and_act,
                    document=document_file
                )
                for document_file in document_list
            ]
            JournalAndActDocuments.objects.bulk_create(documents)
        
        return journal_and_act


class JournalsAndActsUpdateSerializer(FileValidationMixin, serializers.Serializer):
    """
    Сериализатор для обновления JournalsAndActs с документами
    """
    object_id = serializers.PrimaryKeyRelatedField(
        queryset=UserObject.objects.filter(is_deleted=False),
        required=False,
        error_messages={'does_not_exist': 'Объект не найден или удален.'}
    )
    type = serializers.ChoiceField(
        choices=JournalsAndActs.Type.choices,
        required=False,
        allow_null=True,
        help_text='Тип: estimate (Смета), act (Акт), form (Форма)'
    )
    date = serializers.DateField(required=False, allow_null=True)
    document_list = serializers.ListField(
        child=serializers.FileField(),
        required=False,
        allow_empty=True
    )
    
    def to_internal_value(self, data):
        """
        Обработка multipart/form-data для загрузки файлов
        """
        internal_value = {}
        
        # Получаем object_id и конвертируем в UserObject instance (если передан)
        object_id_value = data.get('object_id')
        if object_id_value:
            try:
                object_id = int(object_id_value)
                user_object = UserObject.objects.filter(id=object_id, is_deleted=False).first()
                if not user_object:
                    raise serializers.ValidationError({'object_id': 'Объект не найден или удален.'})
                internal_value['object_id'] = user_object
            except (ValueError, TypeError):
                raise serializers.ValidationError({'object_id': 'Неверный формат ID объекта.'})
        
        internal_value['type'] = data.get('type')
        internal_value['date'] = data.get('date')
        
        # Обрабатываем файлы
        files = self.context.get('files', {})
        document_list = []
        
        request = self.context.get('request')
        if request and hasattr(request, 'FILES'):
            document_list = request.FILES.getlist('document_list')
        
        # Fayllarni validatsiya qilish
        if document_list:
            self.validate_files(document_list)
        
        internal_value['document_list'] = document_list
        return internal_value
    
    def update(self, instance, validated_data):
        """
        Обновление журнала/акта с документами
        Bulk operations ishlatilmoqda - tezroq ishlash uchun
        """
        # Обновляем основные поля
        if 'object_id' in validated_data:
            instance.object_id = validated_data['object_id']
        if 'type' in validated_data:
            instance.type = validated_data['type']
        if 'date' in validated_data:
            instance.date = validated_data['date']
        
        instance.save()
        
        # Если передан document_list, удаляем старые документы и создаем новые
        if 'document_list' in validated_data:
            document_list = validated_data['document_list']
            if document_list:
                # Удаляем старые документы
                instance.journal_and_act_documents.all().delete()
                
                # Bulk create ishlatilmoqda - tezroq ishlash uchun
                documents = [
                    JournalAndActDocuments(
                        journal_and_act_id=instance,
                        document=document_file
                    )
                    for document_file in document_list
                ]
                JournalAndActDocuments.objects.bulk_create(documents)
        
        return instance


class BillsDocumentSerializer(serializers.ModelSerializer):
    """
    Сериализатор для чтения BillDocuments
    """
    document = serializers.SerializerMethodField()
    
    class Meta:
        model = BillDocuments
        fields = ['id', 'document']
        read_only_fields = ['id']
    
    def get_document(self, obj):
        """
        Получение URL документа
        """
        request = self.context.get('request')
        if obj.document and hasattr(obj.document, 'url'):
            if request:
                return request.build_absolute_uri(obj.document.url)
            return obj.document.url
        return None


class BillsSerializer(serializers.ModelSerializer):
    """
    Сериализатор для чтения Bills
    """
    object_id = serializers.SerializerMethodField()
    user = serializers.SerializerMethodField()
    document_list = serializers.SerializerMethodField()
    
    class Meta:
        model = Bills
        fields = [
            'id', 'object_id', 'comment', 'price', 'status', 'user', 'created_at', 'updated_at', 'document_list'
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
    
    def get_document_list(self, obj):
        """
        Получение информации о документах
        """
        documents = obj.bill_documents.all()
        serializer = BillsDocumentSerializer(documents, many=True, context=self.context)
        return serializer.data


class BillsCreateSerializer(FileValidationMixin, serializers.Serializer):
    """
    Сериализатор для создания Bills с документами
    """
    object_id = serializers.PrimaryKeyRelatedField(
        queryset=UserObject.objects.filter(is_deleted=False),
        error_messages={'does_not_exist': 'Объект не найден или удален.'}
    )
    comment = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)
    status = serializers.ChoiceField(choices=Bills.Status.choices, required=False, default=Bills.Status.PENDING)
    document_list = serializers.ListField(
        child=serializers.FileField(),
        required=False,
        allow_empty=True
    )
    
    def to_internal_value(self, data):
        """
        Обработка multipart/form-data для загрузки файлов
        """
        # Получаем object_id и конвертируем в UserObject instance
        object_id_value = data.get('object_id')
        user_object = None
        if object_id_value:
            try:
                object_id = int(object_id_value)
                user_object = UserObject.objects.filter(id=object_id, is_deleted=False).first()
                if not user_object:
                    raise serializers.ValidationError({'object_id': 'Объект не найден или удален.'})
            except (ValueError, TypeError):
                raise serializers.ValidationError({'object_id': 'Неверный формат ID объекта.'})
        else:
            raise serializers.ValidationError({'object_id': 'Это поле обязательно.'})
        
        # price ni Decimal ga aylantirish
        price_value = data.get('price')
        if price_value:
            try:
                from decimal import Decimal
                price_value = Decimal(str(price_value))
            except (ValueError, TypeError):
                price_value = None
        
        # status ni tekshirish
        status_value = data.get('status', Bills.Status.PENDING)
        if status_value not in [choice[0] for choice in Bills.Status.choices]:
            status_value = Bills.Status.PENDING
        
        internal_value = {
            'object_id': user_object,  # UserObject instance
            'comment': data.get('comment', ''),
            'price': price_value,
            'status': status_value,
        }
        
        # Обрабатываем файлы - для multipart/form-data файлы всегда в request.FILES
        files = self.context.get('files', {})
        document_list = []
        
        # Получаем все файлы из request.FILES
        # В form-data файлы могут приходить как:
        # - document_list[0], document_list[1], ... (несколько файлов с индексами)
        # - document_list (один файл или несколько файлов с одним ключом)
        # - document_list[] (массив, один файл)
        
        # Сначала проверяем, есть ли файлы с ключами document_list[0], document_list[1] и т.д.
        document_keys = [key for key in files.keys() if key.startswith('document_list[')]
        if document_keys:
            # Если есть файлы с индексами, сортируем их и добавляем
            document_keys.sort(key=lambda x: int(x.split('[')[1].split(']')[0]) if '[' in x and ']' in x else 0)
            for key in document_keys:
                document_list.append(files[key])
        else:
            # Если нет файлов с индексами, ищем document_list
            # Django'da bir xil key bilan bir nechta fayl yuborilganda, ular list sifatida keladi
            request = self.context.get('request')
            if request and hasattr(request, 'FILES'):
                # getlist() orqali barcha fayllarni olamiz
                document_list = request.FILES.getlist('document_list')
                # Agar getlist() bo'sh bo'lsa, oddiy key bilan qidiramiz
                if not document_list:
                    if 'document_list' in files:
                        # Agar bir fayl bo'lsa, uni list ga aylantiramiz
                        document_list = [files['document_list']]
                    elif 'document_list[]' in files:
                        document_list = [files['document_list[]']]
            else:
                # Agar request yo'q bo'lsa, oddiy files dict dan olamiz
                if 'document_list' in files:
                    # Django'da bir xil key bilan bir nechta fayl yuborilganda, ular list sifatida keladi
                    if isinstance(files['document_list'], list):
                        document_list = files['document_list']
                    else:
                        document_list = [files['document_list']]
                elif 'document_list[]' in files:
                    if isinstance(files['document_list[]'], list):
                        document_list = files['document_list[]']
                    else:
                        document_list = [files['document_list[]']]
        
        # Fayllarni validatsiya qilish
        if document_list:
            self.validate_files(document_list)
        
        internal_value['document_list'] = document_list
        return internal_value
    
    def validate(self, attrs):
        """
        Fayllarni validatsiya qilish
        """
        document_list = attrs.get('document_list', [])
        if document_list:
            self.validate_files(document_list)
        return attrs
    
    def create(self, validated_data):
        """
        Создание счета с документами
        Bulk operations ishlatilmoqda - tezroq ishlash uchun
        """
        user = self.context['request'].user
        object_id = validated_data['object_id']
        comment = validated_data.get('comment', '')
        price = validated_data.get('price')
        status_value = validated_data.get('status', Bills.Status.PENDING)
        document_list = validated_data.get('document_list', [])
        
        # Создаем счет
        bill = Bills.objects.create(
            object_id=object_id,
            user=user,
            comment=comment,
            price=price,
            status=status_value
        )
        
        # Bulk create ishlatilmoqda - tezroq ishlash uchun
        if document_list:
            documents = [
                BillDocuments(
                    bill_id=bill,
                    document=document_file
                )
                for document_file in document_list
            ]
            BillDocuments.objects.bulk_create(documents)
        
        return bill


class BillsUpdateSerializer(FileValidationMixin, serializers.Serializer):
    """
    Сериализатор для обновления Bills с документами
    """
    object_id = serializers.PrimaryKeyRelatedField(
        queryset=UserObject.objects.filter(is_deleted=False),
        required=False,
        error_messages={'does_not_exist': 'Объект не найден или удален.'}
    )
    comment = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)
    status = serializers.ChoiceField(choices=Bills.Status.choices, required=False)
    document_list = serializers.ListField(
        child=serializers.FileField(),
        required=False,
        allow_empty=True
    )
    
    def to_internal_value(self, data):
        """
        Обработка multipart/form-data для загрузки файлов
        """
        internal_value = {}
        
        # Получаем object_id и конвертируем в UserObject instance (если передан)
        object_id_value = data.get('object_id')
        if object_id_value:
            try:
                object_id = int(object_id_value)
                user_object = UserObject.objects.filter(id=object_id, is_deleted=False).first()
                if not user_object:
                    raise serializers.ValidationError({'object_id': 'Объект не найден или удален.'})
                internal_value['object_id'] = user_object
            except (ValueError, TypeError):
                raise serializers.ValidationError({'object_id': 'Неверный формат ID объекта.'})
        
        # price ni Decimal ga aylantirish
        price_value = data.get('price')
        if price_value:
            try:
                from decimal import Decimal
                price_value = Decimal(str(price_value))
            except (ValueError, TypeError):
                price_value = None
            internal_value['price'] = price_value
        
        # status ni tekshirish
        status_value = data.get('status')
        if status_value:
            if status_value not in [choice[0] for choice in Bills.Status.choices]:
                raise serializers.ValidationError({'status': 'Неверный статус.'})
            internal_value['status'] = status_value
        
        internal_value['comment'] = data.get('comment')
        
        # Обрабатываем файлы
        files = self.context.get('files', {})
        document_list = []
        
        request = self.context.get('request')
        if request and hasattr(request, 'FILES'):
            document_list = request.FILES.getlist('document_list')
        
        # Fayllarni validatsiya qilish
        if document_list:
            self.validate_files(document_list)
        
        internal_value['document_list'] = document_list
        return internal_value
    
    def update(self, instance, validated_data):
        """
        Обновление счета с документами
        Bulk operations ishlatilmoqda - tezroq ishlash uchun
        """
        # Обновляем основные поля
        if 'object_id' in validated_data:
            instance.object_id = validated_data['object_id']
        if 'comment' in validated_data:
            instance.comment = validated_data['comment']
        if 'price' in validated_data:
            instance.price = validated_data['price']
        if 'status' in validated_data:
            instance.status = validated_data['status']
        
        instance.save()
        
        # Если передан document_list, удаляем старые документы и создаем новые
        if 'document_list' in validated_data:
            document_list = validated_data['document_list']
            if document_list:
                # Удаляем старые документы
                instance.bill_documents.all().delete()
                
                # Bulk create ishlatilmoqda - tezroq ishlash uchun
                documents = [
                    BillDocuments(
                        bill_id=instance,
                        document=document_file
                    )
                    for document_file in document_list
                ]
                BillDocuments.objects.bulk_create(documents)
        
        return instance

