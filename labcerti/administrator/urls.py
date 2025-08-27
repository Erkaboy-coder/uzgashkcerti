from django.urls import path
from . import views

app_name = 'administrator'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('dashboard/<str:status>/', views.dashboard, name='dashboard_status'),  # draft, pending, approved, rejected
    path("workers/", views.workers_list, name="workers_list"),
    # path('workers/<str:status>/',views.workers_list, name='workers_list_status'),
    path("workers/create/", views.worker_create, name="worker_create"),
    path("workers/<int:pk>/toggle/", views.worker_toggle_status, name="worker_toggle_status"),
    path("workers/<int:pk>/", views.worker_detail, name="worker_detail"),
    path("workers/<int:pk>/delete/", views.worker_delete, name="worker_delete"),

]
