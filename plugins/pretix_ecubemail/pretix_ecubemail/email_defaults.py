# Ecube Access — default email copy applied at organizer level.
# All events under the organizer inherit these unless overridden per-event
# in Settings → E-mail → E-mail content.
#
# Placeholders use Pretix's {placeholder} syntax, not Django templates.
# Markdown bold (**text**) renders correctly via the Ecube HTML renderer.

MAIL_DEFAULTS = {
    # ------------------------------------------------------------------ #
    # 1. Placed order — pending payment                                   #
    # ------------------------------------------------------------------ #
    "mail_subject_order_placed": (
        "Your order {code} for {event} — complete payment by {expire_date}"
    ),
    "mail_text_order_placed": (
        "Hey {name},\n\n"
        "Your order for **{event}** is in — nice move. Here's what you need to know:\n\n"
        "**Order:** {code}\n"
        "**Total:** {total_with_currency}\n"
        "**Payment deadline:** {expire_date}\n\n"
        "{payment_info}\n\n"
        "Complete your payment before the deadline or your reservation will expire. "
        "No pressure — but spots don't wait.\n\n"
        "**View your order and pay here:**\n"
        "{url}\n\n"
        "See you there.\n\n"
        "— Ecube Access"
    ),

    # ------------------------------------------------------------------ #
    # 2. Free order — no payment needed                                   #
    # ------------------------------------------------------------------ #
    "mail_subject_order_free": (
        "You're in — {event} confirmed ({code})"
    ),
    "mail_text_order_free": (
        "Hey {name},\n\n"
        "You're confirmed for **{event}** — no payment needed, you're all set.\n\n"
        "**Order:** {code}\n"
        "**Event:** {event}\n\n"
        "Download your tickets and save them to your phone. You'll need them at the door.\n\n"
        "**Get your tickets here:**\n"
        "{url}\n\n"
        "See you there.\n\n"
        "— Ecube Access"
    ),

    # ------------------------------------------------------------------ #
    # 3. Paid order — payment confirmed                                   #
    # ------------------------------------------------------------------ #
    "mail_subject_order_paid": (
        "Payment confirmed — your tickets for {event} are ready ({code})"
    ),
    "mail_text_order_paid": (
        "Hey {name},\n\n"
        "Payment received. You're locked in for **{event}**.\n\n"
        "**Order:** {code}\n"
        "**Total paid:** {total_with_currency}\n\n"
        "Your tickets are ready to download. Save them to your phone or print them — "
        "you'll need them at the door.\n\n"
        "{payment_info}\n\n"
        "**Download your tickets:**\n"
        "{url}\n\n"
        "This is happening.\n\n"
        "— Ecube Access"
    ),

    # ------------------------------------------------------------------ #
    # 4. Order changed                                                     #
    # ------------------------------------------------------------------ #
    "mail_subject_order_changed": (
        "Your order {code} for {event} has been updated"
    ),
    "mail_text_order_changed": (
        "Hey {name},\n\n"
        "Your order **{code}** for **{event}** has been updated. "
        "The changes are reflected on your order page.\n\n"
        "If this results in a changed total, you'll see the updated amount on your order page "
        "along with payment details if applicable.\n\n"
        "**Review your updated order:**\n"
        "{url}\n\n"
        "Questions? Reply to this email and we'll sort it out.\n\n"
        "— Ecube Access"
    ),

    # ------------------------------------------------------------------ #
    # 5. Order canceled                                                   #
    # ------------------------------------------------------------------ #
    "mail_subject_order_canceled": (
        "Order {code} for {event} has been canceled"
    ),
    "mail_text_order_canceled": (
        "Hey {name},\n\n"
        "Your order **{code}** for **{event}** has been canceled.\n\n"
        "{comment}\n\n"
        "If a refund is due, it will be processed according to the original payment method. "
        "This can take a few business days depending on your bank.\n\n"
        "**View order details:**\n"
        "{url}\n\n"
        "If you didn't request this cancellation or have questions, reply to this email.\n\n"
        "— Ecube Access"
    ),

    # ------------------------------------------------------------------ #
    # 6. Payment reminder — expiration warning                            #
    # ------------------------------------------------------------------ #
    "mail_subject_order_expire_warning": (
        "Reminder: Payment for {event} expires on {expire_date} — order {code}"
    ),
    "mail_text_order_expire_warning": (
        "Hey {name},\n\n"
        "Quick heads-up — your order **{code}** for **{event}** is still waiting for payment.\n\n"
        "**Total due:** {total_with_currency}\n"
        "**Deadline:** {expire_date}\n\n"
        "If we don't receive payment by then, your reservation will expire and your spot "
        "goes back into the pool.\n\n"
        "{payment_info}\n\n"
        "**Pay now:**\n"
        "{url}\n\n"
        "Don't sleep on this.\n\n"
        "— Ecube Access"
    ),

    # ------------------------------------------------------------------ #
    # 7. Download reminder                                                #
    # ------------------------------------------------------------------ #
    "mail_subject_download_reminder": (
        "{event} is coming up — download your tickets now"
    ),
    "mail_text_download_reminder": (
        "Hey {name},\n\n"
        "**{event}** is right around the corner. Make sure your tickets are downloaded and ready.\n\n"
        "**Your order:** {code}\n\n"
        "Pro tip: screenshot your ticket or save the PDF to your phone. "
        "Venue Wi-Fi is never as reliable as you'd like it to be.\n\n"
        "**Download your tickets:**\n"
        "{url}\n\n"
        "See you soon.\n\n"
        "— Ecube Access"
    ),

    # ------------------------------------------------------------------ #
    # 8. Waiting list — voucher available                                 #
    # ------------------------------------------------------------------ #
    "mail_subject_waiting_list": (
        "Your spot just opened up — {product} for {event}"
    ),
    "mail_text_waiting_list": (
        "Hey {name},\n\n"
        "Good news — a spot just opened up for **{product}** at **{event}**.\n\n"
        "We're holding a voucher for you, but it won't last forever. "
        "You have **{hours} hours** to claim it before it goes to the next person in line.\n\n"
        "**Your voucher code:** {code}\n\n"
        "**Claim your spot now:**\n"
        "{url}\n\n"
        "Clock's ticking.\n\n"
        "— Ecube Access"
    ),

    # ------------------------------------------------------------------ #
    # 9. Resend order link                                                #
    # ------------------------------------------------------------------ #
    "mail_subject_resend_link": (
        "Your order link for {event}"
    ),
    "mail_text_resend_link": (
        "Hey {name},\n\n"
        "You requested your order link. Here it is:\n\n"
        "{orders}\n\n"
        "Use this link to view your order status, download tickets, or make changes "
        "(if allowed by the organizer).\n\n"
        "Didn't request this? Just ignore this email — no action needed.\n\n"
        "— Ecube Access"
    ),

    # ------------------------------------------------------------------ #
    # 10. Order requires approval                                         #
    # ------------------------------------------------------------------ #
    "mail_subject_order_placed_require_approval": (
        "Order {code} received — awaiting approval for {event}"
    ),
    "mail_text_order_placed_require_approval": (
        "Hey {name},\n\n"
        "Your order **{code}** for **{event}** has been received and is awaiting "
        "approval from the organizer.\n\n"
        "**Total:** {total_with_currency}\n\n"
        "You'll receive another email once your order has been reviewed. "
        "No payment is needed until the order is approved.\n\n"
        "**View your order:**\n"
        "{url}\n\n"
        "Sit tight — we'll be in touch.\n\n"
        "— Ecube Access"
    ),

    # ------------------------------------------------------------------ #
    # 11. Order approved                                                  #
    # ------------------------------------------------------------------ #
    "mail_subject_order_approved": (
        "Your order {code} for {event} has been approved"
    ),
    "mail_text_order_approved": (
        "Hey {name},\n\n"
        "Great news — your order **{code}** for **{event}** has been approved.\n\n"
        "**Total:** {total_with_currency}\n\n"
        "{payment_info}\n\n"
        "Complete your payment to secure your tickets. "
        "Once paid, you'll receive a confirmation with download links.\n\n"
        "**View your order and pay:**\n"
        "{url}\n\n"
        "You're almost there.\n\n"
        "— Ecube Access"
    ),

    # ------------------------------------------------------------------ #
    # 12. Order denied                                                    #
    # ------------------------------------------------------------------ #
    "mail_subject_order_denied": (
        "Order {code} for {event} — not approved"
    ),
    "mail_text_order_denied": (
        "Hey {name},\n\n"
        "Unfortunately, your order **{code}** for **{event}** was not approved.\n\n"
        "{comment}\n\n"
        "No payment has been charged. If you have questions about why your order wasn't "
        "approved, reply to this email and we'll help clarify.\n\n"
        "— Ecube Access"
    ),
}


def apply_email_defaults(organizer, force=False):
    """Write MAIL_DEFAULTS to organizer-level settings.

    Events inherit these automatically unless they have a per-event override
    set in Settings → E-mail → E-mail content.

    Args:
        organizer: Pretix Organizer instance.
        force:     If True, overwrite keys that already have a value.
                   If False (default), skip keys that are already set.
    """
    applied = []
    skipped = []
    for key, value in MAIL_DEFAULTS.items():
        existing = organizer.settings.get(key)
        if force or not existing:
            organizer.settings.set(key, value)
            applied.append(key)
        else:
            skipped.append(key)
    return applied, skipped
