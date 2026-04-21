from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand

from mailing.models import Client, Message, Mailing
from users.models import User


class Command(BaseCommand):
    help = "Создаёт группу Менеджеры"

    def handle(self, *args, **options):
        group, created = Group.objects.get_or_create(name="Менеджеры")

        # Права для клиентов
        ct = ContentType.objects.get_for_model(Client)
        perm = Permission.objects.get(codename="can_view_all_clients", content_type=ct)
        group.permissions.add(perm)

        # Права для сообщений
        ct = ContentType.objects.get_for_model(Message)
        perm = Permission.objects.get(codename="can_view_all_messages", content_type=ct)
        group.permissions.add(perm)

        # Права для рассылок
        ct = ContentType.objects.get_for_model(Mailing)
        perm1 = Permission.objects.get(
            codename="can_view_all_mailings", content_type=ct
        )
        perm2 = Permission.objects.get(codename="can_disable_mailing", content_type=ct)
        group.permissions.add(perm1, perm2)

        # Право на просмотр пользователей
        ct = ContentType.objects.get_for_model(User)
        perm = Permission.objects.get(codename="view_user", content_type=ct)
        group.permissions.add(perm)

        self.stdout.write(self.style.SUCCESS('Группа "Менеджеры" создана'))
