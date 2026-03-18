from datetime import datetime, time as dt_time
from django import forms
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .models import AdmissionCredential


CREDENTIAL_FIELD_SPECS = [
    {"name": "holder_email", "label": _("Email"), "default_show": True, "default_required": False, "default_print": True},
    {"name": "holder_phone", "label": _("Phone"), "default_show": True, "default_required": False, "default_print": False},
    {"name": "holder_photo", "label": _("Photo"), "default_show": True, "default_required": False, "default_print": True},
    {"name": "credential_type", "label": _("Credential type"), "default_show": True, "default_required": True, "default_print": True},
    {"name": "entry_mode", "label": _("Entry mode"), "default_show": True, "default_required": True, "default_print": True},
    {"name": "label", "label": _("Label"), "default_show": True, "default_required": False, "default_print": True},
    {"name": "notes", "label": _("Notes"), "default_show": True, "default_required": False, "default_print": False},
    {"name": "valid_from", "label": _("Valid from"), "default_show": True, "default_required": False, "default_print": False},
    {"name": "valid_until", "label": _("Valid until"), "default_show": True, "default_required": False, "default_print": True},
]

PRINT_TEMPLATE_CHOICES = [
    ("standard", _("Standard badge")),
    ("compact", _("Compact badge")),
    ("photo_focus", _("Photo focus badge")),
]


def get_credential_form_config(event=None):
    config = {}
    for spec in CREDENTIAL_FIELD_SPECS:
        name = spec["name"]
        show = spec["default_show"]
        required = spec["default_required"]
        include_print = spec["default_print"]

        if event is not None:
            show = event.settings.get(f"admissions_show_{name}", as_type=bool, default=show)
            required = event.settings.get(f"admissions_require_{name}", as_type=bool, default=required)
            include_print = event.settings.get(f"admissions_print_{name}", as_type=bool, default=include_print)

        show = bool(show)
        required = bool(required) if show else False

        config[name] = {
            "show": show,
            "required": required,
            "include_print": bool(include_print),
            "label": spec["label"],
        }
    return config


def get_credential_design_config(event=None):
    data = {
        "print_template": "standard",
        "primary_color": "#ED1C24",
        "accent_color": "#F0EDE8",
    }
    if event is not None:
        data["print_template"] = event.settings.get("admissions_print_template", default=data["print_template"]) or data["print_template"]
        data["primary_color"] = event.settings.get("admissions_primary_color", default=data["primary_color"]) or data["primary_color"]
        data["accent_color"] = event.settings.get("admissions_accent_color", default=data["accent_color"]) or data["accent_color"]
    return data


class _BootstrapMixin:
    def _apply_bootstrap(self):
        for name, field in self.fields.items():
            widget = field.widget

            if isinstance(widget, forms.CheckboxInput):
                continue

            existing = widget.attrs.get("class", "").strip()
            classes = [c for c in existing.split() if c]
            if "form-control" not in classes:
                classes.append("form-control")
            widget.attrs["class"] = " ".join(classes)

            if name == "holder_name":
                widget.attrs.setdefault("placeholder", "Full name")
            elif name == "holder_email":
                widget.attrs.setdefault("placeholder", "Email address")
            elif name == "holder_phone":
                widget.attrs.setdefault("placeholder", "Phone number")
            elif name == "label":
                widget.attrs.setdefault("placeholder", "Optional operational label")
            elif name == "notes":
                widget.attrs.setdefault("placeholder", "Internal notes")
            elif name == "primary_color":
                widget.attrs.setdefault("placeholder", "#ED1C24")
            elif name == "accent_color":
                widget.attrs.setdefault("placeholder", "#F0EDE8")


class AdmissionCredentialForm(_BootstrapMixin, forms.ModelForm):
    valid_from = forms.DateField(
        required=False,
        label=_("Valid from"),
        input_formats=["%Y-%m-%d"],
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    valid_until = forms.DateField(
        required=False,
        label=_("Valid until"),
        input_formats=["%Y-%m-%d"],
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    class Meta:
        model = AdmissionCredential
        fields = [
            "holder_name",
            "holder_email",
            "holder_phone",
            "holder_photo",
            "credential_type",
            "entry_mode",
            "label",
            "notes",
            "valid_from",
            "valid_until",
        ]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 5}),
        }

    def __init__(self, *args, event=None, form_config=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_bootstrap()

        if getattr(self.instance, "pk", None):
            if getattr(self.instance, "valid_from", None):
                self.initial["valid_from"] = self.instance.valid_from.date()
            if getattr(self.instance, "valid_until", None):
                self.initial["valid_until"] = self.instance.valid_until.date()

        config = form_config or get_credential_form_config(event)

        for spec in CREDENTIAL_FIELD_SPECS:
            name = spec["name"]
            if name not in self.fields:
                continue

            if not config[name]["show"]:
                self.fields[name].required = False
                self.fields[name].widget = forms.HiddenInput()
                continue

            self.fields[name].required = config[name]["required"]

        if "holder_name" in self.fields:
            self.fields["holder_name"].required = True

    def _date_to_aware_datetime(self, value, end_of_day=False):
        if not value:
            return None
        dt = datetime.combine(
            value,
            dt_time(23, 59, 59, 999999) if end_of_day else dt_time(0, 0, 0, 0),
        )
        if timezone.is_naive(dt):
            return timezone.make_aware(dt, timezone.get_current_timezone())
        return dt

    def clean_valid_from(self):
        value = self.cleaned_data.get("valid_from")
        return self._date_to_aware_datetime(value, end_of_day=False)

    def clean_valid_until(self):
        value = self.cleaned_data.get("valid_until")
        return self._date_to_aware_datetime(value, end_of_day=True)

class RevokeCredentialForm(_BootstrapMixin, forms.Form):
    reason = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
        label=_("Revocation reason"),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_bootstrap()


class CredentialsSettingsForm(_BootstrapMixin, forms.Form):
    print_template = forms.ChoiceField(
        choices=PRINT_TEMPLATE_CHOICES,
        required=True,
        label=_("Print template"),
    )
    primary_color = forms.CharField(required=False, label=_("Primary color"))
    accent_color = forms.CharField(required=False, label=_("Accent color"))

    def __init__(self, *args, event=None, **kwargs):
        super().__init__(*args, **kwargs)

        design = get_credential_design_config(event)
        self.fields["print_template"].initial = design["print_template"]
        self.fields["primary_color"].initial = design["primary_color"]
        self.fields["accent_color"].initial = design["accent_color"]

        config = get_credential_form_config(event)
        for spec in CREDENTIAL_FIELD_SPECS:
            name = spec["name"]
            label = spec["label"]

            self.fields[f"show_{name}"] = forms.BooleanField(
                required=False,
                label=_("Show: %(field)s") % {"field": label},
                initial=config[name]["show"],
            )
            self.fields[f"require_{name}"] = forms.BooleanField(
                required=False,
                label=_("Require: %(field)s") % {"field": label},
                initial=config[name]["required"],
            )
            self.fields[f"print_{name}"] = forms.BooleanField(
                required=False,
                label=_("Print: %(field)s") % {"field": label},
                initial=config[name]["include_print"],
            )

        self._apply_bootstrap()


class BulkCredentialImportForm(_BootstrapMixin, forms.Form):
    csv_file = forms.FileField(label=_("CSV file"))
    commit_now = forms.BooleanField(
        required=False,
        label=_("Import immediately"),
        help_text=_("Leave unchecked to validate and preview only."),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_bootstrap()

