from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import EmailMessage
from django.conf import settings
from .forms import UserRegistrationForm, UserLoginForm, UserProfileForm
from .models import User
from .tokens import account_activation_token
from django.db.models import Count, Q
from mailings.models import MailingAttempt, Mailing


def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
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
            return redirect('mailings:home')
    else:
        form = UserLoginForm()
    return render(request, 'users/login.html', {'form': form})