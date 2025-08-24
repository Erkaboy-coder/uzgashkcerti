# certificates/urls.py
from django.urls import path, include
from . import views
from django.conf.urls import handler404

from labcerti import views as lab_views

handler404 = lab_views.custom_404_view

urlpatterns = [
    # Auth
    # path('', views.index, name='index'),
    path('login/', views.login_page, name='login'),
    path('logout/', views.user_logout, name='logout'),


    path('profile/', views.user_profile, name='profile'),
    path('creator/', include('labcerti.creator.urls')),
    path('approver/', include('labcerti.approver.urls')),

    path('search/', views.public_certificate_search, name='public_search'),
]

