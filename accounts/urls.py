from django.urls import path
from .views import register, user_login, user_logout, terms, privacy

urlpatterns = [
    path("register/", register, name="register"),
    path("login/", user_login, name="login"),
    path("logout/", user_logout, name="logout"),
    path("terms/", terms, name="terms"),
    path("privacy/", privacy, name="privacy"),
]