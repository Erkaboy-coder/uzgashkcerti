from django.urls import path
from . import views

app_name = 'approver'

urlpatterns = [
    path('dashboard/', views.approver_list, name='dashboard'),
    path('all/', views.approver_list, name='all'),
    path('new/', views.approver_list, name='new', kwargs={'status_filter': 'new'}),
    path('approved/', views.approver_list, name='approved', kwargs={'status_filter': 'approved'}),
    path('rejected/', views.approver_list, name='rejected', kwargs={'status_filter': 'rejected'}),

    path('approve/<int:pk>/', views.approve_certificate, name='approve_certificate'),
    path('reject/<int:pk>/', views.reject_certificate, name='reject_certificate'),
    path('detail/<int:pk>/', views.approver_detail, name='detail'),
]
