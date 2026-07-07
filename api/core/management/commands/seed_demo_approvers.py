from django.core.management.base import BaseCommand

from api.user_management.models import User, UserRole

DEMO_APPROVERS = (
    {
        "email": "jane.ferreira@meridianbank.com",
        "first_name": "Jane",
        "last_name": "Ferreira",
    },
    {
        "email": "marcus.chen@meridianbank.com",
        "first_name": "Marcus",
        "last_name": "Chen",
    },
)


class Command(BaseCommand):
    help = "Seed demo admin approver users referenced by suggested approval PDFs"

    def handle(self, *args, **options):
        del args, options
        created = 0
        updated = 0

        for approver in DEMO_APPROVERS:
            user, was_created = User.objects.get_or_create(
                email=approver["email"],
                defaults={
                    "first_name": approver["first_name"],
                    "last_name": approver["last_name"],
                    "role": UserRole.ADMIN,
                },
            )
            if was_created:
                user.set_unusable_password()
                user.save(update_fields=["password"])
                created += 1
                self.stdout.write(f"Created admin approver {user.email}")
                continue

            fields_to_update = []
            if user.role != UserRole.ADMIN:
                user.role = UserRole.ADMIN
                fields_to_update.append("role")
            if user.first_name != approver["first_name"]:
                user.first_name = approver["first_name"]
                fields_to_update.append("first_name")
            if user.last_name != approver["last_name"]:
                user.last_name = approver["last_name"]
                fields_to_update.append("last_name")
            if fields_to_update:
                user.save(update_fields=fields_to_update)
                updated += 1
                self.stdout.write(f"Updated admin approver {user.email}")
            else:
                self.stdout.write(f"Admin approver already present: {user.email}")

        self.stdout.write(
            self.style.SUCCESS(
                f"Demo approver seed complete ({created} created, {updated} updated)",
            ),
        )
