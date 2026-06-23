from django.urls import path

from chatbot import views


app_name = "chatbot"

urlpatterns = [
    path("", views.chat_view, name="chat"),
    path("envoyer-message/", views.envoyer_message, name="envoyer_message"),
    path("enregistrer-feedback/", views.enregistrer_feedback, name="enregistrer_feedback"),
]
