from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView


urlpatterns = [
    path("admin/", admin.site.urls),
    path("comptes/", include("accounts.urls")),
    path("corpus/", include("corpus.urls")),
    path("dashboard/", include("dashboard.urls")),
    path("", TemplateView.as_view(template_name="base.html"), name="home"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
