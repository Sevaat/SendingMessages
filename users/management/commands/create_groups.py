from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from mailings.models import Mailing, Message, Recipient


class Command(BaseCommand):
    help = 'Создание групп пользователей'

    def handle(self, *args, **options):
        # Создание группы менеджеров
        managers_group, created = Group.objects.get_or_create(name='Менеджеры')

        if created:
            # Получение разрешений для менеджеров
            content_types = [
                ContentType.objects.get_for_model(Mailing),
                ContentType.objects.get_for_model(Message),
                ContentType.objects.get_for_model(Recipient),
            ]

            permissions = Permission.objects.filter(
                content_type__in=content_types,
                codename__in=[
                    'can_view_all_mailings',
                    'can_view_all_messages',
                    'can_view_all_recipients',
                    'can_disable_mailings',
                    'view_mailing',
                    'view_message',
                    'view_recipient',
                ]
            )

            managers_group.permissions.set(permissions)
            self.stdout.write(self.style.SUCCESS('Группа "Менеджеры" успешно создана'))
        else:
            self.stdout.write('Группа "Менеджеры" уже существует')