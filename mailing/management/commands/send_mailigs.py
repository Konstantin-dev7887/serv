import logging

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.utils import timezone

from mailing.models import Mailing, MailingAttempt

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Отправляет активные рассылки"

    def handle(self, *args, **options):
        now = timezone.now()
        mailings = Mailing.objects.filter(
            start_time__lte=now, end_time__gte=now, status="started"
        )
        for mailing in mailings:
            recipients = mailing.recipients.all()
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
                except Exception as e:
                    MailingAttempt.objects.create(
                        mailing=mailing, status="failure", server_response=str(e)
                    )
            self.stdout.write(f"Рассылка {mailing.id} обработана")
