from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path("register/", views.register, name="register"),
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="users/login.html",
            redirect_authenticated_user=True,
        ),
        name="login",
    ),
    # Logout is POST-only in Django 5 (a GET logout can be triggered by
    # any image tag), so the header uses a small form, not a link.
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
]
