from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import EmailMessage
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils import timezone
from .forms import UserRegistrationForm, UserLoginForm, UserProfileForm
from .models import User
from .tokens import account_activation_token
from mailings.models import Mailing, MailingAttempt, Recipient


def register(request):
    """Регистрация нового пользователя"""
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False  # Пользователь неактивен до подтверждения email
            user.save()

            # Отправка email для подтверждения
            current_site = get_current_site(request)
            mail_subject = 'Активация аккаунта'
            message = render_to_string('users/acc_active_email.html', {
                'user': user,
                'domain': current_site.domain,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': account_activation_token.make_token(user),
            })
            to_email = form.cleaned_data.get('email')
            email = EmailMessage(mail_subject, message, to=[to_email])
            email.send()

            messages.success(request, 'Пожалуйста, подтвердите свой email. Проверьте почту.')
            return redirect('users:login')
    else:
        form = UserRegistrationForm()
    return render(request, 'users/register.html', {'form': form})


def activate(request, uidb64, token):
    """Активация аккаунта по ссылке из email"""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        user.is_verified = True
        user.save()
        login(request, user)
        messages.success(request, 'Email подтвержден! Добро пожаловать!')
        return redirect('mailings:home')
    else:
        messages.error(request, 'Ссылка для активации недействительна!')
        return redirect('users:login')


def user_login(request):
    """Вход пользователя в систему"""
    if request.method == 'POST':
        form = UserLoginForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if not user.is_verified:
                messages.error(request, 'Пожалуйста, подтвердите email перед входом')
                return redirect('users:login')
            if user.is_blocked:
                messages.error(request, 'Ваш аккаунт заблокирован. Обратитесь к администратору')
                return redirect('users:login')
            login(request, user)

            # Обновляем время последней активности
            user.last_activity = timezone.now()
            user.save(update_fields=['last_activity'])

            messages.success(request, f'Добро пожаловать, {user.email}!')
            return redirect('mailings:home')
    else:
        form = UserLoginForm()
    return render(request, 'users/login.html', {'form': form})


def user_logout(request):
    """Выход пользователя из системы"""
    logout(request)
    messages.success(request, 'Вы успешно вышли из системы')
    return redirect('mailings:home')


@login_required
def profile(request):
    """Просмотр профиля пользователя"""
    return render(request, 'users/profile.html', {'user': request.user})


@login_required
def profile_edit(request):
    """Редактирование профиля пользователя"""
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Профиль успешно обновлен')
            return redirect('users:profile')
    else:
        form = UserProfileForm(instance=request.user)
    return render(request, 'users/profile_edit.html', {'form': form})


@staff_member_required
def user_list(request):
    """Список всех пользователей для менеджеров"""
    users = User.objects.all().order_by('-date_joined')

    # Фильтрация
    status = request.GET.get('status')
    if status == 'active':
        users = users.filter(is_active=True, is_blocked=False)
    elif status == 'blocked':
        users = users.filter(is_blocked=True)
    elif status == 'unverified':
        users = users.filter(is_verified=False)

    # Поиск
    search = request.GET.get('search')
    if search:
        users = users.filter(
            Q(email__icontains=search) |
            Q(phone__icontains=search) |
            Q(country__icontains=search)
        )

    # Пагинация
    paginator = Paginator(users, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'total_users': User.objects.count(),
        'active_users': User.objects.filter(is_active=True, is_blocked=False).count(),
        'blocked_users': User.objects.filter(is_blocked=True).count(),
        'unverified_users': User.objects.filter(is_verified=False).count(),
    }
    return render(request, 'users/user_list.html', context)


@staff_member_required
def user_detail(request, pk):
    """Детальная информация о пользователе для менеджеров"""
    user = get_object_or_404(User, pk=pk)

    # Статистика пользователя
    total_mailings = Mailing.objects.filter(owner=user).count()
    active_mailings = Mailing.objects.filter(
        owner=user,
        start_time__lte=timezone.now(),
        end_time__gte=timezone.now()
    ).count()

    attempts = MailingAttempt.objects.filter(mailing__owner=user)
    total_attempts = attempts.count()
    success_attempts = attempts.filter(status='success').count()

    context = {
        'target_user': user,
        'total_mailings': total_mailings,
        'active_mailings': active_mailings,
        'total_attempts': total_attempts,
        'success_attempts': success_attempts,
        'failed_attempts': total_attempts - success_attempts,
    }
    return render(request, 'users/user_detail.html', context)


@staff_member_required
def toggle_user_block(request, pk):
    """Блокировка/разблокировка пользователя"""
    if request.method == 'POST':
        user = get_object_or_404(User, pk=pk)
        if user == request.user:
            messages.error(request, 'Нельзя заблокировать самого себя')
            return redirect('users:user_detail', pk=pk)

        user.is_blocked = not user.is_blocked
        user.save()

        action = 'заблокирован' if user.is_blocked else 'разблокирован'
        messages.success(request, f'Пользователь {user.email} {action}')

    return redirect('users:user_detail', pk=pk)


@staff_member_required
def disable_user_mailings(request, user_pk):
    """Отключение всех рассылок пользователя"""
    if request.method == 'POST':
        user = get_object_or_404(User, pk=user_pk)
        mailings = Mailing.objects.filter(owner=user, status='running')

        count = mailings.update(status='completed')
        messages.success(request, f'Отключено {count} активных рассылок')

    return redirect('users:user_detail', pk=user_pk)
