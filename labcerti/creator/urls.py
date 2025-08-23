# creator/urls.py
from django.urls import path
from . import views

app_name = 'creator'

urlpatterns = [
    path('', views.dashboard, name='all'),
    path('sent/', views.dashboard, {'status_filter': 'pending'}, name='sent'),
    path('approved/', views.dashboard, {'status_filter': 'approved'}, name='approved'),
    path('rejected/', views.dashboard, {'status_filter': 'rejected'}, name='rejected'),

    path('certificate/<int:pk>/', views.certificate_detail, name='detail'),
    path('certificate/<int:pk>/edit/', views.edit_certificate, name='edit'),
    path('create/', views.create_certificate, name='create'),
    path('delete/<int:pk>/', views.delete_certificate, name='delete'),
]
