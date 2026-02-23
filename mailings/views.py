from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from .models import Message, Recipient, Mailing, MailingAttempt
from .forms import MessageForm, RecipientForm, MailingForm
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings


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


@login_required
def mailing_attempts(request, pk):
    mailing = get_object_or_404(Mailing, pk=pk)
    attempts = MailingAttempt.objects.filter(mailing=mailing)
    return render(request, 'mailings/mailing_attempts.html', {'mailing': mailing, 'attempts': attempts})


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