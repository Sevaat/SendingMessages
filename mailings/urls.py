from django.urls import path
from . import views

app_name = 'mailings'

urlpatterns = [
    path('', views.home, name='home'),

    # Сообщения
    path('messages/', views.message_list, name='message_list'),
    path('messages/create/', views.message_create, name='message_create'),
    path('messages/<int:pk>/edit/', views.message_edit, name='message_edit'),
    path('messages/<int:pk>/delete/', views.message_delete, name='message_delete'),

    # Получатели
    path('recipients/', views.recipient_list, name='recipient_list'),
    path('recipients/create/', views.recipient_create, name='recipient_create'),
    path('recipients/<int:pk>/edit/', views.recipient_edit, name='recipient_edit'),
    path('recipients/<int:pk>/delete/', views.recipient_delete, name='recipient_delete'),

    # Рассылки
    path('mailings/', views.mailing_list, name='mailing_list'),
    path('mailings/create/', views.mailing_create, name='mailing_create'),
    path('mailings/<int:pk>/edit/', views.mailing_edit, name='mailing_edit'),
    path('mailings/<int:pk>/delete/', views.mailing_delete, name='mailing_delete'),
    path('mailings/<int:pk>/send/', views.send_mailing, name='send_mailing'),
    path('mailings/<int:pk>/attempts/', views.mailing_attempts, name='mailing_attempts'),

    # Попытки (общий список)
    path('attempts/', views.attempt_list, name='attempt_list'),

    # Статистика
    path('statistics/', views.user_statistics, name='user_statistics'),
    path('mailings/<int:pk>/statistics/', views.mailing_statistics, name='mailing_statistics'),
]