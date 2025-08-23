# project urls.py
from django.contrib import admin
from django.urls import path, include,re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('labcerti.urls')),  
    re_path(r'^data/labcerti/(?P<path>.*)', serve,{'document_root': settings.DATA_LABCERTI_ROOT}),
    re_path(r'^data/centercerti/(?P<path>.*)', serve,{'document_root': settings.DATA_CENTER_ROOT}),
]



if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_URL)