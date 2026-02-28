from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.utils import timezone
from django.conf import settings
from mailings.models import Mailing, MailingAttempt


class Command(BaseCommand):
    help = 'Отправка запланированных рассылок'

    def handle(self, *args, **options):
        now = timezone.now()

        # Получаем активные рассылки, которые нужно отправить
        mailings = Mailing.objects.filter(
            start_time__lte=now,
            end_time__gte=now,
        )

        for mailing in mailings:
            self.stdout.write(f'Обработка рассылки #{mailing.id}')

            successful = 0
            failed = 0

            for recipient in mailing.recipients.all():
                try:
                    send_mail(
                        subject=mailing.message.subject,
                        message=mailing.message.body,
                        from_email=settings.EMAIL_HOST_USER,
                        recipient_list=[recipient.email],
                        fail_silently=False,
                    )
                    MailingAttempt.objects.create(
                        mailing=mailing,
                        status=MailingAttempt.Status.SUCCESS,
                        server_response='Успешно отправлено'
                    )
                    successful += 1
                except Exception as e:
                    MailingAttempt.objects.create(
                        mailing=mailing,
                        status=MailingAttempt.Status.FAILED,
                        server_response=str(e)
                    )
                    failed += 1

            self.stdout.write(
                self.style.SUCCESS(
                    f'Рассылка #{mailing.id} обработана. '
                    f'Успешно: {successful}, Ошибок: {failed}'
                )
            )