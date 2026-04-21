from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import Mailing


class MailingForm(forms.ModelForm):
    class Meta:
        model = Mailing
        fields = ["start_time", "end_time", "message", "recipients"]
        widgets = {
            "start_time": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "end_time": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }

    def clean_start_time(self):
        start_time = self.cleaned_data["start_time"]
        if start_time < timezone.now():
            raise ValidationError("Дата начала не может быть в прошлом.")
        return start_time

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get("start_time")
        end = cleaned_data.get("end_time")
        if start and end and start >= end:
            raise ValidationError("Дата начала должна быть раньше даты окончания.")
        return cleaned_data
