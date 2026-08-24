from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST


def register(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        password2 = request.POST.get("password2", "")

        if not username or not password or not password2:
            return render(request, "accounts/register.html", {"error": "Please fill in all fields."})

        if len(username) < 3:
            return render(request, "accounts/register.html", {"error": "Username must be at least 3 characters."})

        if password != password2:
            return render(request, "accounts/register.html", {"error": "Passwords do not match."})

        if User.objects.filter(username__iexact=username).exists():
            return render(request, "accounts/register.html", {"error": "Username already exists."})

        try:
            validate_password(password)
        except ValidationError as exc:
            return render(request, "accounts/register.html", {"error": " ".join(exc.messages)})

        User.objects.create_user(username=username, password=password)
        messages.success(request, "Account created successfully. Please sign in.")
        return redirect("login")

    return render(request, "accounts/register.html")


def user_login(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect("products")

        return render(request, "accounts/login.html", {"error": "Invalid username or password."})

    return render(request, "accounts/login.html")


@require_POST
def user_logout(request):
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect("login")

def terms(request):
    return render(request, "accounts/terms.html")

def privacy(request):
    return render(request, "accounts/privacy.html")
