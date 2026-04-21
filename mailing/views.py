from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.mail import send_mail
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView,
    TemplateView,
)

from .forms import MailingForm
from .models import Client, Message, Mailing, MailingAttempt


class OwnerRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        obj = self.get_object()
        user = self.request.user
        if user.has_perm("mailing.can_view_all_mailings") and self.request.method in [
            "GET",
            "HEAD",
            "OPTIONS",
        ]:
            return True
        return obj.owner == user


@method_decorator(cache_page(60 * 15), name="dispatch")
class HomeView(TemplateView):
    template_name = "mailing/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        if user.is_authenticated:
            mailings = Mailing.objects.filter(owner=user)
            context["total_mailings"] = mailings.count()
            context["active_mailings"] = mailings.filter(status="started").count()
            clients = Client.objects.filter(owner=user)
            context["unique_clients"] = clients.distinct().count()
        return context


# Клиенты
class ClientListView(LoginRequiredMixin, ListView):
    model = Client
    template_name = "mailing/client_list.html"
    context_object_name = "clients"

    def get_queryset(self):
        user = self.request.user
        if user.has_perm("mailing.can_view_all_clients"):
            return Client.objects.all()
        return Client.objects.filter(owner=user)


class ClientDetailView(LoginRequiredMixin, OwnerRequiredMixin, DetailView):
    model = Client
    template_name = "mailing/client_detail.html"


class ClientCreateView(LoginRequiredMixin, CreateView):
    model = Client
    fields = ["email", "full_name", "comment"]
    template_name = "mailing/client_form.html"
    success_url = reverse_lazy("mailing:client_list")

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)


class ClientUpdateView(LoginRequiredMixin, OwnerRequiredMixin, UpdateView):
    model = Client
    fields = ["email", "full_name", "comment"]
    template_name = "mailing/client_form.html"
    success_url = reverse_lazy("mailing:client_list")


class ClientDeleteView(LoginRequiredMixin, OwnerRequiredMixin, DeleteView):
    model = Client
    template_name = "mailing/client_confirm_delete.html"
    success_url = reverse_lazy("mailing:client_list")


# Сообщения
class MessageListView(LoginRequiredMixin, ListView):
    model = Message
    template_name = "mailing/message_list.html"
    context_object_name = "messages_list"

    def get_queryset(self):
        user = self.request.user
        if user.has_perm("mailing.can_view_all_messages"):
            return Message.objects.all()
        return Message.objects.filter(owner=user)


class MessageDetailView(LoginRequiredMixin, OwnerRequiredMixin, DetailView):
    model = Message
    template_name = "mailing/message_detail.html"


class MessageCreateView(LoginRequiredMixin, CreateView):
    model = Message
    fields = ["subject", "body"]
    template_name = "mailing/message_form.html"
    success_url = reverse_lazy("mailing:message_list")

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)


class MessageUpdateView(LoginRequiredMixin, OwnerRequiredMixin, UpdateView):
    model = Message
    fields = ["subject", "body"]
    template_name = "mailing/message_form.html"
    success_url = reverse_lazy("mailing:message_list")


class MessageDeleteView(LoginRequiredMixin, OwnerRequiredMixin, DeleteView):
    model = Message
    template_name = "mailing/message_confirm_delete.html"
    success_url = reverse_lazy("mailing:message_list")


# Рассылки
class MailingListView(LoginRequiredMixin, ListView):
    model = Mailing
    template_name = "mailing/mailing_list.html"
    context_object_name = "mailings"

    def get_queryset(self):
        user = self.request.user
        if user.has_perm("mailing.can_view_all_mailings"):
            return Mailing.objects.all()
        return Mailing.objects.filter(owner=user)


class MailingDetailView(LoginRequiredMixin, OwnerRequiredMixin, DetailView):
    model = Mailing
    template_name = "mailing/mailing_detail.html"

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        obj.update_status()
        return obj


class MailingCreateView(LoginRequiredMixin, CreateView):
    model = Mailing
    form_class = MailingForm
    template_name = "mailing/mailing_form.html"
    success_url = reverse_lazy("mailing:mailing_list")

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)


class MailingUpdateView(LoginRequiredMixin, OwnerRequiredMixin, UpdateView):
    model = Mailing
    form_class = MailingForm
    template_name = "mailing/mailing_form.html"
    success_url = reverse_lazy("mailing:mailing_list")


class MailingDeleteView(LoginRequiredMixin, OwnerRequiredMixin, DeleteView):
    model = Mailing
    template_name = "mailing/mailing_confirm_delete.html"
    success_url = reverse_lazy("mailing:mailing_list")


def send_mailing_now(request, pk):
    mailing = get_object_or_404(Mailing, pk=pk)
    if request.user != mailing.owner and not request.user.has_perm(
        "mailing.can_view_all_mailings"
    ):
        messages.error(request, "Нет прав.")
        return redirect("mailing:mailing_list")
    mailing.update_status()
    if mailing.status != "started":
        messages.error(request, "Рассылка не активна.")
        return redirect("mailing:mailing_detail", pk=pk)
    recipients = mailing.recipients.all()
    success_count = 0
    for client in recipients:
        try:
            send_mail(
                subject=mailing.message.subject,
                message=mailing.message.body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[client.email],
                fail_silently=False,
            )
            MailingAttempt.objects.create(
                mailing=mailing, status="success", server_response="OK"
            )
            success_count += 1
        except Exception as e:
            MailingAttempt.objects.create(
                mailing=mailing, status="failure", server_response=str(e)
            )
    messages.success(request, f"Отправлено: {success_count} из {recipients.count()}")
    return redirect("mailing:mailing_detail", pk=pk)


class MailingAttemptListView(LoginRequiredMixin, ListView):
    model = MailingAttempt
    template_name = "mailing/attempt_list.html"
    context_object_name = "attempts"

    def get_queryset(self):
        user = self.request.user
        if user.has_perm("mailing.can_view_all_mailings"):
            return MailingAttempt.objects.all().order_by("-attempt_time")
        return MailingAttempt.objects.filter(mailing__owner=user).order_by(
            "-attempt_time"
        )
