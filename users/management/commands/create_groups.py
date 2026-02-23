from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q

from mailings.models import Mailing, Message, Recipient
from users.models import User


class Command(BaseCommand):
    help = 'Создание групп пользователей и прав'

    def handle(self, *args, **options):
        # Создание группы менеджеров
        managers_group, created = Group.objects.get_or_create(name='Менеджеры')

        if created:
            # Получение разрешений для моделей рассылок
            mailing_ct = ContentType.objects.get_for_model(Mailing)
            message_ct = ContentType.objects.get_for_model(Message)
            recipient_ct = ContentType.objects.get_for_model(Recipient)
            user_ct = ContentType.objects.get_for_model(User)

            permissions = Permission.objects.filter(
                Q(content_type=mailing_ct, codename__in=[
                    'view_mailing', 'can_view_all_mailings', 'can_disable_mailings'
                ]) |
                Q(content_type=message_ct, codename__in=[
                    'view_message', 'can_view_all_messages'
                ]) |
                Q(content_type=recipient_ct, codename__in=[
                    'view_recipient', 'can_view_all_recipients'
                ]) |
                Q(content_type=user_ct, codename__in=[
                    'view_user', 'can_block_user', 'can_view_all_users'
                ])
            )

            managers_group.permissions.set(permissions)
            self.stdout.write(self.style.SUCCESS('Группа "Менеджеры" успешно создана'))
        else:
            self.stdout.write('Группа "Менеджеры" уже существует')