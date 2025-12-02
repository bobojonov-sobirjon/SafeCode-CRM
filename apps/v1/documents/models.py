from django.db import models
from apps.v1.accounts.models import CustomUser
from apps.v1.user_objects.models import UserObject


class JournalsAndActs(models.Model):
    """
    Журналы и акты
    """
    
    class Type(models.TextChoices):
        ESTIMATE = 'estimate', 'Смета'
        ACT = 'act', 'Акт'
        FORM = 'form', 'Форма'
        
    object_id = models.ForeignKey(
        UserObject,
        on_delete=models.CASCADE,
        related_name='journals_and_acts',
        verbose_name='Объект'
    )
    type = models.CharField(
        max_length=255,
        verbose_name='Тип',
        null=True,
        blank=True,
        choices=Type.choices
    )
    date = models.DateField(
        verbose_name='Дата',
        null=True,
        blank=True
    )
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='journals_and_acts',
        verbose_name='Пользователь'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    
    objects = models.Manager()
    
    class Meta:
        verbose_name = 'Журнал и акт'
        verbose_name_plural = 'Журналы и акты'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at'], name='journals_user_created_idx'),
            models.Index(fields=['object_id', '-created_at'], name='journals_object_created_idx'),
            models.Index(fields=['object_id', 'user'], name='journals_object_user_idx'),
        ]
    
    def __str__(self):
        return f"Журнал/Акт #{self.id} - {self.object_id.name if self.object_id else 'N/A'}"


class JournalAndActDocuments(models.Model):
    """
    Документы журнала и акта
    """
    journal_and_act_id = models.ForeignKey(
        JournalsAndActs,
        on_delete=models.CASCADE,
        related_name='journal_and_act_documents',
    )
    document = models.FileField(
        upload_to='journal_and_act_documents/',
        verbose_name='Документ',
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )
    objects = models.Manager()
    
    class Meta:
        verbose_name = 'Документ журнала и акта'
        verbose_name_plural = 'Документы журнала и акта'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Документ #{self.id} - {self.journal_and_act_id.object_id.name if self.journal_and_act_id.object_id else 'N/A'}"


class Bills(models.Model):
    """
    Счета
    """
    class Status(models.TextChoices):
        PENDING = 'pending', 'Ожидание'
        PAID = 'paid', 'Оплачен'
        CANCELLED = 'cancelled', 'Отменен'
    
    object_id = models.ForeignKey(
        UserObject,
        on_delete=models.CASCADE,
        related_name='bills',
        verbose_name='Объект'
    )
    comment = models.TextField(
        verbose_name='Комментарий',
        null=True,
        blank=True
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Цена',
        null=True,
        blank=True
    )
    status = models.CharField(
        max_length=255,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name='Статус'
    )
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='bills',
        verbose_name='Пользователь'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )
    
    objects = models.Manager()
    
    class Meta:
        verbose_name = 'Счет'
        verbose_name_plural = 'Счета'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at'], name='bills_user_created_idx'),
            models.Index(fields=['object_id', '-created_at'], name='bills_object_created_idx'),
            models.Index(fields=['status', '-created_at'], name='bills_status_created_idx'),
            models.Index(fields=['object_id', 'user'], name='bills_object_user_idx'),
        ]
    
    def __str__(self):
        return f"Счет #{self.id} - {self.object_id.name if self.object_id else 'N/A'}"


class BillDocuments(models.Model):
    """
    Документы счета
    """
    bill_id = models.ForeignKey(
        Bills,
        on_delete=models.CASCADE,
        related_name='bill_documents',
    )
    document = models.FileField(
        upload_to='bill_documents/',
        verbose_name='Документ',
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )
    objects = models.Manager()  
    
    class Meta:
        verbose_name = 'Документ счета'
        verbose_name_plural = 'Документы счета'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Документ #{self.id} - {self.bill_id.object_id.name if self.bill_id.object_id else 'N/A'}"