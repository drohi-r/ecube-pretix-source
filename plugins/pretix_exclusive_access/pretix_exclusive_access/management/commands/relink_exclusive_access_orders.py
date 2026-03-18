import re
from django.core.management.base import BaseCommand
from django_scopes import scope

from pretix.base.models import Organizer, Event
from pretix.base.models.orders import OrderPosition
from pretix_exclusive_access.models import ExclusiveAccessApplication, ApplicationStatus


def norm(v):
    v = (v or "").strip().lower()
    v = re.sub(r"\s+", " ", v)
    return v


class Command(BaseCommand):
    help = "Relink approved Exclusive Access applications to Pretix order positions."

    def add_arguments(self, parser):
        parser.add_argument("--organizer", required=True)
        parser.add_argument("--event", required=True)
        parser.add_argument("--apply", action="store_true")
        parser.add_argument("--app-id", type=int)
        parser.add_argument("--limit", type=int, default=100)

    def handle(self, *args, **opts):
        organizer = Organizer.objects.get(slug=opts["organizer"])

        with scope(organizer=organizer):
            event = Event.objects.get(slug=opts["event"])

            qs = ExclusiveAccessApplication.objects.filter(
                event=event,
                status=ApplicationStatus.APPROVED,
            ).select_related("item", "approved_order_position")

            if opts.get("app_id"):
                qs = qs.filter(id=opts["app_id"])
            else:
                qs = qs.filter(approved_order_position__isnull=True)

            qs = qs.order_by("-created_at")[: opts["limit"]]

            linked = 0
            skipped = 0
            ambiguous = 0

            self.stdout.write(f"Event: {event.slug}")
            self.stdout.write(f"Applications to inspect: {qs.count()}")
            self.stdout.write("-" * 80)

            for app in qs:
                app_name = norm(app.full_name)
                app_email = norm(app.email)

                candidates = (
                    OrderPosition.objects
                    .filter(order__event=event, item=app.item)
                    .select_related("order", "item")
                    .order_by("-order__datetime", "-pk")
                )

                scored = []
                for pos in candidates:
                    score = 0

                    attendee_email = norm(getattr(pos, "attendee_email", ""))
                    order_email = norm(getattr(pos.order, "email", ""))
                    attendee_name = norm(getattr(pos, "attendee_name", ""))

                    if app_email and attendee_email and app_email == attendee_email:
                        score += 100
                    if app_email and order_email and app_email == order_email:
                        score += 90
                    if app_name and attendee_name and app_name == attendee_name:
                        score += 80

                    if score > 0:
                        scored.append((score, pos))

                scored.sort(key=lambda x: (-x[0], -(x[1].order.datetime.timestamp() if x[1].order.datetime else 0), -x[1].pk))

                best = scored[0] if scored else None
                second = scored[1] if len(scored) > 1 else None

                summary = {
                    "app_id": app.id,
                    "name": app.full_name,
                    "email": app.email,
                    "item": str(app.item),
                    "has_photo": bool(app.photo),
                }

                if not best:
                    skipped += 1
                    self.stdout.write(f"NO MATCH: {summary}")
                    continue

                best_score, best_pos = best
                ambiguous_hit = second and second[0] == best_score

                if ambiguous_hit:
                    ambiguous += 1
                    self.stdout.write(
                        f"AMBIGUOUS: {summary} -> "
                        f"best {best_pos.order.code}-{best_pos.positionid} score={best_score}, "
                        f"second {second[1].order.code}-{second[1].positionid} score={second[0]}"
                    )
                    continue

                self.stdout.write(
                    f"MATCH: {summary} -> "
                    f"{best_pos.order.code}-{best_pos.positionid} "
                    f"(score={best_score}, attendee={getattr(best_pos, 'attendee_name', '')}, "
                    f"attendee_email={getattr(best_pos, 'attendee_email', '')}, order_email={best_pos.order.email})"
                )

                if opts["apply"]:
                    app.approved_order_code = best_pos.order.code
                    app.approved_order_position = best_pos
                    app.save(update_fields=["approved_order_code", "approved_order_position", "updated_at"])
                    linked += 1

            self.stdout.write("-" * 80)
            if opts["apply"]:
                self.stdout.write(self.style.SUCCESS(f"LINKED: {linked}"))
            else:
                self.stdout.write(self.style.WARNING("DRY RUN ONLY"))
            self.stdout.write(f"SKIPPED: {skipped}")
            self.stdout.write(f"AMBIGUOUS: {ambiguous}")
