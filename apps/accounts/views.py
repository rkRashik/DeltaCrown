from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic import FormView, TemplateView

from .forms import SignUpForm


class DCLoginView(LoginView):
    template_name = "accounts/login.html"


class DCLogoutView(LogoutView):
    next_page = reverse_lazy("homepage")


class SignUpView(FormView):
    template_name = "accounts/signup.html"
    form_class = SignUpForm
    success_url = reverse_lazy("accounts:profile")

    def form_valid(self, form):
        user = form.save()
        # Auto-login
        raw_password = form.cleaned_data["password1"]
        user = authenticate(self.request, username=user.username, password=raw_password)
        if user:
            login(self.request, user)
        messages.success(self.request, "Welcome to DeltaCrown!")
        return super().form_valid(form)


@login_required
def profile_view(request: HttpRequest) -> HttpResponse:
    return render(request, "accounts/profile.html", {})
