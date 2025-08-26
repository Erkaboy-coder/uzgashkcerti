# creator/urls.py
from django.urls import path
from . import views

app_name = 'creator'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('dashboard/<str:status>/', views.dashboard, name='dashboard_status'),  # draft, pending, approved, rejected

    path('certificate/<int:pk>/', views.certificate_detail, name='detail'),
    path('certificate/<int:pk>/edit/', views.edit_certificate, name='edit'),
    path('create/', views.create_certificate, name='create'),
    path('delete/<int:pk>/', views.delete_certificate, name='delete'),
    path('resend/<int:pk>/', views.resend_rejected_certificate, name='resend_certificate'),

]
