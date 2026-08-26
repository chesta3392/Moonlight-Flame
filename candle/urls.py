from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic.base import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('favicon.ico', RedirectView.as_view(url='/media/favicon.ico', permanent=True)),
    path('favicon-32x32.png', RedirectView.as_view(url='/media/favicon-32x32.png', permanent=True)),
    path('apple-touch-icon.png', RedirectView.as_view(url='/media/apple-touch-icon.png', permanent=True)),
    path('', include('store.urls')),
    path('accounts/', include('accounts.urls')),
]

from django.views.static import serve
from django.urls import re_path

urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {
        'document_root': settings.MEDIA_ROOT,
    }),
]