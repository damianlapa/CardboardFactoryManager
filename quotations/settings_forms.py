from django import forms

from .models import FefcoType


class SheetRuleSelectForm(forms.Form):
    packaging_type = forms.ModelChoiceField(
        label="Kod FEFCO",
        queryset=FefcoType.objects.order_by("code"),
        empty_label="— Wybierz FEFCO —",
    )


class SheetRuleRowForm(forms.Form):
    glue_flap = forms.DecimalField(
        label="Zakładka (mm)",
        max_digits=7,
        decimal_places=2,
        min_value=0,
        required=False,
    )
    length_allowance = forms.DecimalField(
        label="Dodatek do długości (mm)",
        max_digits=7,
        decimal_places=2,
        min_value=0,
        required=False,
    )
    width_allowance = forms.DecimalField(
        label="Dodatek do szerokości (mm)",
        max_digits=7,
        decimal_places=2,
        min_value=0,
        required=False,
    )

    def __init__(
        self,
        *args,
        configured=False,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self.configured = configured

        for field in self.fields.values():
            field.widget.attrs.update({
                "min": "0",
                "step": "0.01",
                "placeholder": "—",
                "aria-label": field.label,
            })

    def clean(self):
        data = super().clean()

        if self.errors:
            return data

        values = [
            data.get(name)
            for name in self.fields
        ]

        filled = sum(
            value is not None
            for value in values
        )

        if (
            (filled and filled != 3)
            or (self.configured and filled == 0)
        ):
            raise forms.ValidationError(
                "Uzupełnij wszystkie trzy dodatki "
                "dla tej fali. Jeśli dodatku nie ma, "
                "wpisz 0."
            )

        return data