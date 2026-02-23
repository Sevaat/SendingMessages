from django.core.cache import cache
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_cookie

from .models import Message, Recipient, Mailing, MailingAttempt
from .forms import MessageForm, RecipientForm, MailingForm
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta


# Главная страница
@cache_page(60 * 15)
@vary_on_cookie
def home(request):
    total_mailings = Mailing.objects.count()
    active_mailings = Mailing.objects.filter(
        start_time__lte=timezone.now(),
        end_time__gte=timezone.now()
    ).count()
    unique_recipients = Recipient.objects.values('email').distinct().count()

    context = {
        'total_mailings': total_mailings,
        'active_mailings': active_mailings,
        'unique_recipients': unique_recipients,
    }
    return render(request, 'mailings/home.html', context)


# CRUD для сообщений
@login_required
def message_list(request):
    if request.user.has_perm('mailings.can_view_all_messages'):
        messages_list = Message.objects.all()
    else:
        messages_list = Message.objects.filter(owner=request.user)
    return render(request, 'mailings/message_list.html', {'messages': messages_list})


@login_required
def message_create(request):
    if request.method == 'POST':
        form = MessageForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            message.owner = request.user
            message.save()
            messages.success(request, 'Сообщение успешно создано')
            return redirect('mailings:message_list')
    else:
        form = MessageForm()
    return render(request, 'mailings/message_form.html', {'form': form, 'title': 'Создание сообщения'})


@login_required
def message_edit(request, pk):
    message = get_object_or_404(Message, pk=pk)
    if message.owner != request.user and not request.user.has_perm('mailings.can_view_all_messages'):
        raise PermissionDenied

    if request.method == 'POST':
        form = MessageForm(request.POST, instance=message)
        if form.is_valid():
            form.save()
            messages.success(request, 'Сообщение успешно обновлено')
            return redirect('mailings:message_list')
    else:
        form = MessageForm(instance=message)
    return render(request, 'mailings/message_form.html', {'form': form, 'title': 'Редактирование сообщения'})


@login_required
def message_delete(request, pk):
    message = get_object_or_404(Message, pk=pk)
    if message.owner != request.user and not request.user.has_perm('mailings.can_view_all_messages'):
        raise PermissionDenied

    if request.method == 'POST':
        message.delete()
        messages.success(request, 'Сообщение удалено')
        return redirect('mailings:message_list')
    return render(request, 'mailings/message_confirm_delete.html', {'message': message})


# CRUD для получателей
@login_required
def recipient_list(request):
    if request.user.has_perm('mailings.can_view_all_recipients'):
        recipients = Recipient.objects.all()
    else:
        recipients = Recipient.objects.filter(owner=request.user)
    return render(request, 'mailings/recipient_list.html', {'recipients': recipients})


@login_required
def recipient_create(request):
    if request.method == 'POST':
        form = RecipientForm(request.POST)
        if form.is_valid():
            recipient = form.save(commit=False)
            recipient.owner = request.user
            recipient.save()
            messages.success(request, 'Получатель успешно создан')
            return redirect('mailings:recipient_list')
    else:
        form = RecipientForm()
    return render(request, 'mailings/recipient_form.html', {'form': form, 'title': 'Создание получателя'})


@login_required
def recipient_edit(request, pk):
    recipient = get_object_or_404(Recipient, pk=pk)
    if recipient.owner != request.user and not request.user.has_perm('mailings.can_view_all_recipients'):
        raise PermissionDenied

    if request.method == 'POST':
        form = RecipientForm(request.POST, instance=recipient)
        if form.is_valid():
            form.save()
            messages.success(request, 'Получатель успешно обновлен')
            return redirect('mailings:recipient_list')
    else:
        form = RecipientForm(instance=recipient)
    return render(request, 'mailings/recipient_form.html', {'form': form, 'title': 'Редактирование получателя'})


@login_required
def recipient_delete(request, pk):
    recipient = get_object_or_404(Recipient, pk=pk)
    if recipient.owner != request.user and not request.user.has_perm('mailings.can_view_all_recipients'):
        raise PermissionDenied

    if request.method == 'POST':
        recipient.delete()
        messages.success(request, 'Получатель удален')
        return redirect('mailings:recipient_list')
    return render(request, 'mailings/recipient_confirm_delete.html', {'recipient': recipient})


# CRUD для рассылок
@login_required
def mailing_list(request):
    cache_key = f'mailing_list_user_{request.user.id}'
    mailings = cache.get(cache_key)
    if not mailings:
        if request.user.has_perm('mailings.can_view_all_mailings'):
            mailings = Mailing.objects.all().select_related('message', 'owner')
        else:
            mailings = Mailing.objects.filter(owner=request.user).select_related('message')

        cache.set(cache_key, mailings, 300)

    return render(request, 'mailings/mailing_list.html', {'mailings': mailings})


@login_required
def mailing_create(request):
    if request.method == 'POST':
        form = MailingForm(request.POST, user=request.user)
        if form.is_valid():
            mailing = form.save(commit=False)
            mailing.owner = request.user
            mailing.save()
            form.save_m2m()  # Сохраняем связи многие-ко-многим
            messages.success(request, 'Рассылка успешно создана')
            return redirect('mailings:mailing_list')
    else:
        form = MailingForm(user=request.user)
    return render(request, 'mailings/mailing_form.html', {'form': form, 'title': 'Создание рассылки'})


@login_required
def mailing_edit(request, pk):
    mailing = get_object_or_404(Mailing, pk=pk)
    if mailing.owner != request.user and not request.user.has_perm('mailings.can_view_all_mailings'):
        raise PermissionDenied

    if request.method == 'POST':
        form = MailingForm(request.POST, instance=mailing, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Рассылка успешно обновлена')
            return redirect('mailings:mailing_list')
    else:
        form = MailingForm(instance=mailing, user=request.user)
    return render(request, 'mailings/mailing_form.html', {'form': form, 'title': 'Редактирование рассылки'})


@login_required
def mailing_delete(request, pk):
    mailing = get_object_or_404(Mailing, pk=pk)
    if mailing.owner != request.user and not request.user.has_perm('mailings.can_view_all_mailings'):
        raise PermissionDenied

    if request.method == 'POST':
        mailing.delete()
        messages.success(request, 'Рассылка удалена')
        return redirect('mailings:mailing_list')
    return render(request, 'mailings/mailing_confirm_delete.html', {'mailing': mailing})


@login_required
def send_mailing(request, pk):
    mailing = get_object_or_404(Mailing, pk=pk)

    if mailing.owner != request.user and not request.user.has_perm('mailings.can_disable_mailings'):
        raise PermissionDenied

    if mailing.status != Mailing.Status.RUNNING:
        messages.error(request, 'Рассылка не может быть отправлена в данный момент')
        return redirect('mailings:mailing_list')

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

    messages.success(request, f'Рассылка завершена. Успешно: {successful}, Ошибок: {failed}')
    return redirect('mailings:mailing_attempts', pk=mailing.pk)


# Просмотр попыток
@login_required
def mailing_attempts(request, pk):
    mailing = get_object_or_404(Mailing, pk=pk)
    if mailing.owner != request.user and not request.user.has_perm('mailings.can_view_all_mailings'):
        raise PermissionDenied

    attempts = MailingAttempt.objects.filter(mailing=mailing)
    return render(request, 'mailings/mailing_attempts.html', {
        'mailing': mailing,
        'attempts': attempts
    })


@login_required
def attempt_list(request):
    """Общий список всех попыток для пользователя"""
    if request.user.has_perm('mailings.can_view_all_mailings'):
        # Для менеджеров показываем все попытки
        attempts = MailingAttempt.objects.all().select_related('mailing', 'mailing__message')
    else:
        # Для обычных пользователей показываем только попытки их рассылок
        attempts = MailingAttempt.objects.filter(
            mailing__owner=request.user
        ).select_related('mailing', 'mailing__message')

    return render(request, 'mailings/attempt_list.html', {'attempts': attempts})


@cache_page(60 * 5)
@login_required
def user_statistics(request):
    """Статистика для текущего пользователя"""
    user = request.user

    # Основные показатели
    total_mailings = Mailing.objects.filter(owner=user).count()
    active_mailings = Mailing.objects.filter(
        owner=user,
        start_time__lte=timezone.now(),
        end_time__gte=timezone.now()
    ).count()

    # Статистика по попыткам
    user_mailings = Mailing.objects.filter(owner=user)
    attempts = MailingAttempt.objects.filter(mailing__in=user_mailings)

    total_attempts = attempts.count()
    success_attempts = attempts.filter(status='success').count()
    failed_attempts = attempts.filter(status='failed').count()

    success_rate = 0
    if total_attempts > 0:
        success_rate = (success_attempts / total_attempts) * 100

    # Статистика по получателям
    total_recipients = Recipient.objects.filter(owner=user).count()

    # Статистика по дням (последние 7 дней)
    last_week = timezone.now() - timedelta(days=7)
    daily_stats = MailingAttempt.objects.filter(
        mailing__owner=user,
        attempt_time__gte=last_week
    ).extra({'date': "date(attempt_time)"}).values('date').annotate(
        total=Count('id'),
        success=Count('id', filter=Q(status='success')),
        failed=Count('id', filter=Q(status='failed'))
    ).order_by('date')

    # Лучшие рассылки по успешности
    top_mailings = Mailing.objects.filter(owner=user).annotate(
        attempts_count=Count('attempts'),
        success_count=Count('attempts', filter=Q(attempts__status='success'))
    ).order_by('-success_count')[:5]

    context = {
        'total_mailings': total_mailings,
        'active_mailings': active_mailings,
        'total_attempts': total_attempts,
        'success_attempts': success_attempts,
        'failed_attempts': failed_attempts,
        'success_rate': round(success_rate, 2),
        'total_recipients': total_recipients,
        'daily_stats': daily_stats,
        'top_mailings': top_mailings,
    }

    return render(request, 'mailings/statistics.html', context)


@login_required
def mailing_statistics(request, pk):
    """Детальная статистика по конкретной рассылке"""
    mailing = get_object_or_404(Mailing, pk=pk)

    if mailing.owner != request.user and not request.user.has_perm('mailings.can_view_all_mailings'):
        raise PermissionDenied

    attempts = MailingAttempt.objects.filter(mailing=mailing)

    # Общая статистика
    total_attempts = attempts.count()
    success_attempts = attempts.filter(status='success').count()
    failed_attempts = attempts.filter(status='failed').count()

    # Статистика по получателям
    recipients_stats = []
    for recipient in mailing.recipients.all():
        recipient_attempts = attempts.filter(mailing=mailing)
        # Здесь нужно добавить логику для определения успешности по каждому получателю
        recipients_stats.append({
            'recipient': recipient,
            'status': 'success'  # Заглушка, нужно реализовать
        })

    context = {
        'mailing': mailing,
        'total_attempts': total_attempts,
        'success_attempts': success_attempts,
        'failed_attempts': failed_attempts,
        'recipients_stats': recipients_stats,
    }

    return render(request, 'mailings/mailing_statistics.html', context)

def invalidate_user_cache(user_id):
    """Инвалидация кеша пользователя"""
    cache.delete(f'mailing_list_user_{user_id}')
    cache.delete(f'recipient_list_user_{user_id}')
    cache.delete(f'message_list_user_{user_id}')
