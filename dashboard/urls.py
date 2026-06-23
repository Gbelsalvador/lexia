from django.urls import path

from dashboard import views


app_name = "dashboard"

urlpatterns = [
    path("", views.home, name="home"),
    path("utilisateurs/", views.utilisateurs_pme, name="utilisateurs_pme"),
    path(
        "conversations/<int:pk>/",
        views.conversation_detail,
        name="conversation_detail",
    ),
]
