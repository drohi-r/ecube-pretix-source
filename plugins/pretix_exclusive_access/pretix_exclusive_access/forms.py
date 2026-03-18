from django import forms
from django.utils.translation import gettext_lazy as _

from .models import ExclusiveAccessApplication


PUBLIC_FORM_FIELD_SPECS = [
    {"name": "phone", "label": _("Phone"), "default_show": True, "default_required": True},
    {"name": "instagram_handle", "label": _("Instagram / Social"), "default_show": True, "default_required": True},
    {"name": "photo", "label": _("Photo"), "default_show": True, "default_required": True},
    {"name": "gender", "label": _("Gender"), "default_show": True, "default_required": False},
    {"name": "referred_by", "label": _("Referred by"), "default_show": True, "default_required": False},
    {"name": "notes", "label": _("Notes"), "default_show": True, "default_required": False},
]


def get_exclusive_access_form_config(event=None):
    config = {}
    for spec in PUBLIC_FORM_FIELD_SPECS:
        name = spec["name"]
        show = spec["default_show"]
        required = spec["default_required"]

        if event is not None:
            show = event.settings.get(
                f"exclusive_access_show_{name}",
                as_type=bool,
                default=spec["default_show"],
            )
            required = event.settings.get(
                f"exclusive_access_require_{name}",
                as_type=bool,
                default=spec["default_required"],
            )

        show = bool(show)
        required = bool(required) if show else False

        config[name] = {
            "show": show,
            "required": required,
            "label": spec["label"],
        }
    return config


class ExclusiveAccessApplicationForm(forms.ModelForm):
    item = forms.ChoiceField(
        choices=[],
        required=True,
        label=_("Ticket type"),
    )

    gender = forms.ChoiceField(
        required=False,
        label=_("Gender"),
        choices=[
            ("", _("---------")),
            ("male", _("Male")),
            ("female", _("Female")),
        ],
    )

    class Meta:
        model = ExclusiveAccessApplication
        fields = [
            "full_name",
            "gender",
            "email",
            "phone",
            "instagram_handle",
            "photo",
            "referred_by",
            "notes",
        ]

    def __init__(self, *args, protected_items=None, event=None, form_config=None, **kwargs):
        super().__init__(*args, **kwargs)
        protected_items = list(protected_items or [])
        self._protected_item_map = {str(i.pk): i for i in protected_items}
        self.fields["item"].choices = [(str(i.pk), str(i.name)) for i in protected_items]

        config = form_config or get_exclusive_access_form_config(event)
        for name, meta in config.items():
            if name not in self.fields:
                continue
            if not meta["show"]:
                self.fields.pop(name, None)
                continue
            self.fields[name].required = meta["required"]

        desired_order = [
            "item",
            "full_name",
            "gender",
            "email",
            "phone",
            "instagram_handle",
            "photo",
            "referred_by",
            "notes",
        ]
        self.order_fields([f for f in desired_order if f in self.fields])

    def clean_item(self):
        value = self.cleaned_data.get("item")
        item = self._protected_item_map.get(str(value))
        if not item:
            raise forms.ValidationError(_("Please select a valid ticket type."))
        return item

    def clean_photo(self):
        photo = self.cleaned_data.get("photo")
        if not photo:
            return photo
        if photo.size > 10 * 1024 * 1024:
            raise forms.ValidationError(_("Photo must be 10 MB or smaller."))
        allowed = {"image/jpeg", "image/png", "image/webp"}
        if getattr(photo, "content_type", "") not in allowed:
            raise forms.ValidationError(_("Upload a JPG, PNG, or WEBP image."))
        return photo
