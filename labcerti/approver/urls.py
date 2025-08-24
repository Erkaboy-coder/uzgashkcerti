from django.urls import path
from . import views

app_name = 'approver'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('dashboard/<str:status>/', views.dashboard, name='dashboard_status'),  # draft, pending, approved, rejected

    path('approve/<int:pk>/', views.approve_certificate, name='approve_certificate'),
    path('reject/<int:pk>/', views.reject_certificate, name='reject_certificate'),
    path('detail/<int:pk>/', views.approver_detail, name='detail'),
]
