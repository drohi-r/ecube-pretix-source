from django import forms

from .models import EcubeAccessDoor


class ScanTestForm(forms.Form):
    payload = forms.CharField(
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Scan payload"}),
        required=True,
    )
    action = forms.ChoiceField(
        choices=(
            ("entry", "Entry"),
            ("exit", "Exit"),
        ),
        initial="entry",
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    gate = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Gate"}),
    )
    operator_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Operator name"}),
    )
    device_id = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Device ID"}),
    )


class EcubeAccessDoorForm(forms.ModelForm):
    access_pin = forms.CharField(
        required=False,
        strip=True,
        widget=forms.PasswordInput(
            render_value=False,
            attrs={"class": "form-control", "placeholder": "Optional door PIN or password"},
        ),
        help_text="Leave blank to keep the current door PIN/password.",
    )
    access_pin_confirm = forms.CharField(
        required=False,
        strip=True,
        widget=forms.PasswordInput(
            render_value=False,
            attrs={"class": "form-control", "placeholder": "Confirm new door PIN or password"},
        ),
    )
    clear_access_pin = forms.BooleanField(
        required=False,
        label="Remove current door PIN/password",
    )

    def __init__(self, *args, **kwargs):
        self.event = kwargs.pop("event", None)
        super().__init__(*args, **kwargs)
        self.fields["is_active"].widget.attrs["class"] = ""
        self.fields["clear_access_pin"].widget.attrs["class"] = ""

        if not getattr(self.instance, "pk", None):
            self.fields["access_pin"].help_text = "Set an optional PIN/password required before the public door scanner opens."

    class Meta:
        model = EcubeAccessDoor
        fields = ["name", "slug", "default_action", "is_active", "notes"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Main Gate"}),
            "slug": forms.TextInput(attrs={"class": "form-control", "placeholder": "main-gate"}),
            "default_action": forms.Select(attrs={"class": "form-control"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 4, "placeholder": "Optional operator notes"}),
        }

    def clean_slug(self):
        slug = (self.cleaned_data.get("slug") or "").strip()
        if not slug:
            return slug

        if self.event is None:
            return slug

        qs = EcubeAccessDoor.objects.filter(event=self.event, slug=slug)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError("A door with this slug already exists for this event.")
        return slug

    def clean(self):
        cleaned = super().clean()
        pin = (cleaned.get("access_pin") or "").strip()
        pin_confirm = (cleaned.get("access_pin_confirm") or "").strip()
        clear_pin = bool(cleaned.get("clear_access_pin"))

        if clear_pin and pin:
            raise forms.ValidationError("Either clear the current door PIN/password or enter a new one, not both.")

        if pin or pin_confirm:
            if pin != pin_confirm:
                raise forms.ValidationError("Door PIN/password confirmation does not match.")
            if len(pin) < 4:
                raise forms.ValidationError("Door PIN/password must be at least 4 characters long.")

        return cleaned

    def save(self, commit=True):
        door = super().save(commit=False)
        pin = (self.cleaned_data.get("access_pin") or "").strip()
        clear_pin = bool(self.cleaned_data.get("clear_access_pin"))

        if not (door.public_auth_nonce or "").strip():
            door.rotate_public_auth_nonce()

        if clear_pin:
            door.clear_access_pin()
            door.rotate_public_auth_nonce()
        elif pin:
            door.set_access_pin(pin)
            door.rotate_public_auth_nonce()

        if commit:
            door.save()
        return door

