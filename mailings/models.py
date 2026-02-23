from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from users.models import User

class Recipient(models.Model):
    """Модель получателя рассылки"""
    email = models.EmailField(unique=True, verbose_name='Email')
    full_name = models.CharField(max_length=255, verbose_name='Ф.И.О.')
    comment = models.TextField(blank=True, verbose_name='Комментарий')
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recipients',
                              verbose_name='Владелец', null=True)

    class Meta:
        verbose_name = 'Получатель'
        verbose_name_plural = 'Получатели'
        permissions = [
            ('can_view_all_recipients', 'Может просматривать всех получателей'),
        ]

    def __str__(self):
        return self.full_name

class Message(models.Model):
    """Модель сообщения для рассылки"""
    subject = models.CharField(max_length=255, verbose_name='Тема письма')
    body = models.TextField(verbose_name='Тело письма')
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='messages',
                              verbose_name='Владелец', null=True)

    class Meta:
        verbose_name = 'Сообщение'
        verbose_name_plural = 'Сообщения'
        permissions = [
            ('can_view_all_messages', 'Может просматривать все сообщения'),
        ]

    def __str__(self):
        return self.subject

class Mailing(models.Model):
    """Модель рассылки"""
    class Status(models.TextChoices):
        CREATED = 'created', 'Создана'
        RUNNING = 'running', 'Запущена'
        COMPLETED = 'completed', 'Завершена'

    start_time = models.DateTimeField(verbose_name='Дата и время начала')
    end_time = models.DateTimeField(verbose_name='Дата и время окончания')
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='mailings',
                                verbose_name='Сообщение')
    recipients = models.ManyToManyField(Recipient, related_name='mailings',
                                       verbose_name='Получатели')
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mailings',
                              verbose_name='Владелец', null=True)

    class Meta:
        verbose_name = 'Рассылка'
        verbose_name_plural = 'Рассылки'
        permissions = [
            ('can_view_all_mailings', 'Может просматривать все рассылки'),
            ('can_disable_mailings', 'Может отключать рассылки'),
        ]

    def __str__(self):
        return f"Рассылка #{self.id} - {self.message.subject}"

    @property
    def status(self):
        now = timezone.now()
        if now < self.start_time:
            return self.Status.CREATED
        elif self.start_time <= now <= self.end_time:
            return self.Status.RUNNING
        else:
            return self.Status.COMPLETED

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.start_time and self.end_time:
            if self.start_time >= self.end_time:
                raise ValidationError('Дата начала должна быть раньше даты окончания')
            if self.start_time < timezone.now():
                raise ValidationError('Дата начала не может быть в прошлом')

class MailingAttempt(models.Model):
    """Модель попытки рассылки"""
    class Status(models.TextChoices):
        SUCCESS = 'success', 'Успешно'
        FAILED = 'failed', 'Не успешно'

    attempt_time = models.DateTimeField(auto_now_add=True, verbose_name='Дата и время попытки')
    status = models.CharField(max_length=20, choices=Status.choices, verbose_name='Статус')
    server_response = models.TextField(blank=True, verbose_name='Ответ сервера')
    mailing = models.ForeignKey(Mailing, on_delete=models.CASCADE, related_name='attempts',
                                verbose_name='Рассылка')

    class Meta:
        verbose_name = 'Попытка рассылки'
        verbose_name_plural = 'Попытки рассылок'
        ordering = ['-attempt_time']

    def __str__(self):
        return f"Попытка #{self.id} - {self.get_status_display()} - {self.attempt_time}"

    @property
    def success_attempts_count(self):
        return self.attempts.filter(status='success').count()

    @property
    def failed_attempts_count(self):
        return self.attempts.filter(status='failed').count()

    @property
    def total_attempts_count(self):
        return self.attempts.count()

    @property
    def success_rate(self):
        total = self.total_attempts_count
        if total == 0:
            return 0
        return (self.success_attempts_count / total) * 100