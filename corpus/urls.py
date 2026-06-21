from django.urls import path

from corpus import views


app_name = "corpus"

urlpatterns = [
    path("", views.liste_documents, name="liste_documents"),
    path("upload/", views.upload_document, name="upload"),
]
