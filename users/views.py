from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, TemplateView, UpdateView

from .forms import CustomUserCreationForm, ProfileUpdateForm
from .models import User


class RegisterView(CreateView):
    model = User
    form_class = CustomUserCreationForm
    template_name = "users/register.html"
    success_url = reverse_lazy("mailing:home")

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        return redirect(self.success_url)


class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = "users/profile.html"


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = ProfileUpdateForm
    template_name = "users/profile_form.html"
    success_url = reverse_lazy("users:profile")

    def get_object(self, queryset=None):
        return self.request.user
