from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect
from .forms import UserRegisterForm


def register(request):
    if request.method == "POST":
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("login")
    else:
        form = UserRegisterForm()
    return render(request, "users/register.html", {"form": form})


def user_login(request):
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect("home")  # Adjust 'home' to your desired URL name
        else:
            return render(
                request, "users/login.html", {"error": "Invalid username or password"}
            )
    else:
        return render(request, "users/login.html")
