"""
Mixin'lar va helper funksiyalar kod takrorlanishini kamaytirish uchun
"""
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from rest_framework.response import Response
from rest_framework import status


class PaginationMixin:
    """
    Pagination logikasini birlashtiruvchi Mixin
    """
    DEFAULT_PAGE_SIZE = 10
    MAX_PAGE_SIZE = 100
    
    def paginate_queryset(self, queryset, request, page_size=None):
        """
        Queryset'ni paginate qilish
        
        Args:
            queryset: Django QuerySet
            request: DRF Request object
            page_size: Sahifa o'lchami (default: DEFAULT_PAGE_SIZE)
        
        Returns:
            tuple: (page_obj, paginator)
        """
        if page_size is None:
            page_size = self.DEFAULT_PAGE_SIZE
        
        page = request.query_params.get('page', 1)
        limit = request.query_params.get('limit', page_size)
        
        try:
            page = int(page)
            limit = int(limit)
            # Limit'ni cheklash
            if limit > self.MAX_PAGE_SIZE:
                limit = self.MAX_PAGE_SIZE
            if limit < 1:
                limit = page_size
        except ValueError:
            page = 1
            limit = page_size
        
        paginator = Paginator(queryset, limit)
        
        try:
            page_obj = paginator.page(page)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
        
        return page_obj, paginator
    
    def get_paginated_response(self, page_obj, paginator, serializer_data, message='Успешно'):
        """
        Paginated response yaratish
        
        Args:
            page_obj: Paginator page object
            paginator: Paginator instance
            serializer_data: Serialized data
            message: Success message
        
        Returns:
            Response: DRF Response object
        """
        return Response({
            'success': True,
            'message': message,
            'data': serializer_data,
            'pagination': {
                'current_page': page_obj.number,
                'total_pages': paginator.num_pages,
                'total_items': paginator.count,
                'items_per_page': paginator.per_page,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
            }
        }, status=status.HTTP_200_OK)


class FileValidationMixin:
    """
    File validation logikasini birlashtiruvchi Mixin
    """
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS = ['.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png', '.xls', '.xlsx', '.txt']
    
    def validate_files(self, files):
        """
        Fayllarni validatsiya qilish
        
        Args:
            files: Fayllar ro'yxati
        
        Raises:
            serializers.ValidationError: Agar fayl validatsiyadan o'tmasa
        """
        from rest_framework import serializers
        
        if not files:
            return
        
        for file in files:
            # Fayl hajmini tekshirish
            if file.size > self.MAX_FILE_SIZE:
                raise serializers.ValidationError({
                    'document_list': f'Файл {file.name} слишком большой. Максимальный размер: {self.MAX_FILE_SIZE / (1024 * 1024)}MB'
                })
            
            # Fayl formatini tekshirish
            file_extension = None
            if '.' in file.name:
                file_extension = '.' + file.name.rsplit('.', 1)[1].lower()
            
            if file_extension and file_extension not in self.ALLOWED_EXTENSIONS:
                raise serializers.ValidationError({
                    'document_list': f'Недопустимый формат файла {file.name}. Разрешенные форматы: {", ".join(self.ALLOWED_EXTENSIONS)}'
                })
            
            # Fayl nomini tozalash
            from django.utils.text import get_valid_filename
            file.name = get_valid_filename(file.name)

