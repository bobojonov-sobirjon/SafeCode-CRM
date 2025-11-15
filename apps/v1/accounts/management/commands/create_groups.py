from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group


class Command(BaseCommand):
    help = 'Создание групп пользователей'

    def handle(self, *args, **options):
        # Список групп для создания
        groups_to_create = [
            'Дежурный инженер',
            'Заказчик',
            'Инспектор МЧС',
            'Менеджер',
            'Обслуживающий инженер',
            'Исполнителя',
        ]
        
        created_count = 0
        existing_count = 0
        
        for group_name in groups_to_create:
            group, created = Group.objects.get_or_create(name=group_name)
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Группа "{group_name}" создана')
                )
                created_count += 1
            else:
                self.stdout.write(
                    self.style.WARNING(f'Группа "{group_name}" уже существует')
                )
                existing_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'\nГруппы пользователей готовы! '
                f'Создано: {created_count}, Уже существует: {existing_count}'
            )
        )
