"""Authentication views.

Django's built-in `LoginView`/`LogoutView` do the fiddly parts correctly
(`?next=` handling, session rotation, POST-only logout), so they are
wired up in urls.py and only registration keeps hand-written logic here.

The 2024 versions of these views redirected to a URL name that did not
exist, so a successful login crashed; that whole path is gone.
"""

from django.contrib.auth import login
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

from .forms import UserRegisterForm


def safe_next(request):
    """The `?next=` target, but only if it points back at this site.

    An unchecked `next` is an open redirect — a phishing link could send
    a freshly logged-in user to an attacker's page.
    """
    target = request.POST.get("next") or request.GET.get("next") or ""
    if target and url_has_allowed_host_and_scheme(
        target, allowed_hosts={request.get_host()}, require_secure=request.is_secure()
    ):
        return target
    return None


def register(request):
    """Create an account and log straight in — a new DM should land in
    the app, not on a second login form."""
    if request.user.is_authenticated:
        return redirect("campaign_list")

    if request.method == "POST":
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect(safe_next(request) or "campaign_list")
    else:
        form = UserRegisterForm()

    return render(
        request, "users/register.html", {"form": form, "next": safe_next(request) or ""}
    )
