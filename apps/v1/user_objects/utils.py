from .models import UserObject, UserObjectWorkers, UserObjectDocuments, UserObjectDocumentItems
from apps.v1.accounts.models import CustomUser
from django.conf import settings


def get_user_objects_queryset(user):
    """
    Получение queryset объектов пользователя в зависимости от его роли
    
    Если пользователь в группе "Заказчик" - возвращает его собственные объекты
    Если пользователь в других группах - возвращает объекты, где он является работником
    """
    # Проверяем, является ли пользователь Заказчиком
    is_customer = user.groups.filter(name='Заказчик').exists()
    is_admin = user.groups.filter(name='Администратор').exists()
    
    if is_customer:
        # Заказчик видит только свои объекты
        queryset = UserObject.objects.filter(user=user, is_deleted=False).select_related('user')
    elif is_admin:
        # Администратор видит все объекты
        queryset = UserObject.objects.filter(is_deleted=False).select_related('user')
    else:
        # Другие роли видят объекты, где они являются работниками
        worker_objects = UserObjectWorkers.objects.filter(
            user=user
        ).select_related('user_object', 'user_object__user').values_list('user_object_id', flat=True)
        
        queryset = UserObject.objects.filter(
            id__in=worker_objects,
            is_deleted=False
        ).select_related('user')
    
    return queryset


def apply_user_objects_filters(queryset, request):
    """
    Применение фильтров к queryset объектов пользователя
    """
    # Фильтрация по name
    name = request.query_params.get('name', None)
    if name:
        queryset = queryset.filter(name__icontains=name)
    
    # Фильтрация по address
    address = request.query_params.get('address', None)
    if address:
        queryset = queryset.filter(address__icontains=address)
    
    # Фильтрация по size
    size = request.query_params.get('size', None)
    if size:
        try:
            size = float(size)
            queryset = queryset.filter(size=size)
        except ValueError:
            pass
    
    # Фильтрация по number_of_fire_extinguishing_systems
    number_of_systems = request.query_params.get('number_of_fire_extinguishing_systems', None)
    if number_of_systems:
        try:
            number_of_systems = int(number_of_systems)
            queryset = queryset.filter(number_of_fire_extinguishing_systems=number_of_systems)
        except ValueError:
            pass
    
    # Фильтрация по status
    status_filter = request.query_params.get('status', None)
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    
    return queryset


def get_workers_document_data(user_object, request):
    """
    Получение данных о работниках и их документах для объекта
    """
    # Роли для группировки
    roles = [
        'Дежурный инженер',
        'Инспектор МЧС',
        'Исполнителя',
        'Менеджер',
        'Обслуживающий инженер'
    ]
    
    # Получаем всех работников объекта
    workers = UserObjectWorkers.objects.filter(
        user_object=user_object
    ).select_related('user').prefetch_related('user__groups')
    
    # Группируем работников по ролям
    workers_by_role = {}
    for role in roles:
        workers_by_role[role] = {
            'user_info': [],
            'is_send': False,
            'document_list': []
        }
    
    # Обрабатываем каждого работника
    for worker in workers:
        user = worker.user
        user_groups = list(user.groups.values_list('name', flat=True))
        
        # Находим роль работника
        user_role = None
        for role in roles:
            if role in user_groups:
                user_role = role
                break
        
        if not user_role:
            continue
        
        # Добавляем информацию о пользователе
        user_info = {
            'id': user.id,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            'phone_number': user.phone_number
        }
        workers_by_role[user_role]['user_info'].append(user_info)
        
        # Проверяем, отправлял ли пользователь документы
        user_documents = UserObjectDocuments.objects.filter(
            user_object=user_object,
            user=user
        ).prefetch_related('user_object_document_items')
        
        if user_documents.exists():
            # Если хотя бы один пользователь в роли отправил документы, is_send = True
            workers_by_role[user_role]['is_send'] = True
            
            # Получаем все документы пользователя
            for doc in user_documents:
                # Получаем элементы документа
                items = doc.user_object_document_items.all()
                document_urls = []
                for item in items:
                    if item.document:
                        # Формируем полный URL
                        if request:
                            document_url = request.build_absolute_uri(item.document.url)
                        else:
                            document_url = item.document.url
                        document_urls.append({
                            'document_url': document_url
                        })
                
                workers_by_role[user_role]['document_list'].append({
                    'comment': doc.comment or '',
                    'items': document_urls
                })
    
    # Удаляем пустые роли
    result = {}
    for role, data in workers_by_role.items():
        if data['user_info']:  # Если есть хотя бы один работник
            result[role] = data
    
    return result

