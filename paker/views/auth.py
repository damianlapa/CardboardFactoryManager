# paker/views/auth.py

from django.contrib.auth import (
    authenticate,
    login,
    logout,
)
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View

from paker.access.common import get_home_url_name


class LoginView(View):
    template_name = "auth/login.html"

    def get(self, request):
        if request.user.is_authenticated:
            return redirect(
                get_home_url_name(request.user)
            )

        return render(
            request,
            self.template_name,
            {
                "next_url": request.GET.get(
                    "next",
                    "",
                ),
            },
        )

    def post(self, request):
        username = (
            request.POST.get("username")
            or ""
        ).strip()

        password = (
            request.POST.get("password")
            or ""
        )

        next_url = (
            request.POST.get("next")
            or ""
        )

        user = authenticate(
            request,
            username=username,
            password=password,
        )

        if user is None:
            return render(
                request,
                self.template_name,
                {
                    "next_url": next_url,
                    "username": username,
                    "login_error": (
                        "Nieprawidłowy login lub hasło."
                    ),
                },
                status=401,
            )

        login(
            request,
            user,
        )

        if (
            next_url
            and url_has_allowed_host_and_scheme(
                url=next_url,
                allowed_hosts={
                    request.get_host(),
                },
                require_https=request.is_secure(),
            )
        ):
            return redirect(next_url)

        return redirect(
            get_home_url_name(user)
        )


class LogoutView(View):

    def post(self, request):
        logout(request)

        return redirect("login")


class RootView(View):
    def get(self, request):
        if not request.user.is_authenticated:
            return redirect("login")

        return redirect(
            get_home_url_name(request.user)
        )
