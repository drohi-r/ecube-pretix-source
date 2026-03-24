from django.core.management.base import BaseCommand, CommandError
from django_scopes import scopes_disabled

from pretix_ecubemail.email_defaults import apply_email_defaults


class Command(BaseCommand):
    help = (
        "Apply Ecube email copy defaults to organizer-level settings. "
        "Events inherit these automatically; per-event overrides in "
        "Settings → E-mail → E-mail content still take precedence."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--organizer",
            type=str,
            default=None,
            metavar="SLUG",
            help="Apply to a specific organizer slug only (default: all organizers).",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            default=False,
            help="Overwrite keys that already have a value (default: skip existing).",
        )

    def handle(self, *args, **options):
        from pretix.base.models import Organizer

        with scopes_disabled():
            if options["organizer"]:
                orgs = Organizer.objects.filter(slug=options["organizer"])
                if not orgs.exists():
                    raise CommandError(
                        f"No organizer found with slug '{options['organizer']}'"
                    )
            else:
                orgs = Organizer.objects.all()

            for org in orgs:
                applied, skipped = apply_email_defaults(org, force=options["force"])
                self.stdout.write(
                    self.style.SUCCESS(f"[{org.slug}] Applied {len(applied)} key(s), "
                                       f"skipped {len(skipped)} already-set key(s).")
                )
                if options["verbosity"] >= 2:
                    for k in applied:
                        self.stdout.write(f"  SET   {k}")
                    for k in skipped:
                        self.stdout.write(f"  SKIP  {k}")
