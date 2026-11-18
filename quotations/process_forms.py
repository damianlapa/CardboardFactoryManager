from django import forms

from .models import (
    QuotationProcessProfile,
    QuotationProcessFluteRule,
)


class ProcessProfileForm(forms.ModelForm):
    class Meta:
        model = QuotationProcessProfile
        fields = (
            "setup_minutes",
            "setup_workers",
            "run_workers",
            "first_batch_quantity",
            "full_speed_area",
            "min_speed_area",
        )

    def clean(self):
        data = super().clean()

        start = data.get("full_speed_area")
        end = data.get("min_speed_area")

        if (
            start is not None
            and end is not None
            and end <= start
        ):
            self.add_error(
                "min_speed_area",
                "Ten próg musi być większy od progu "
                "pełnego tempa.",
            )

        return data


class ProcessFluteRuleForm(forms.ModelForm):
    class Meta:
        model = QuotationProcessFluteRule
        fields = (
            "first_batch_minutes",
            "max_speed",
            "min_speed",
        )

    def clean(self):
        data = super().clean()

        maximum = data.get("max_speed")
        minimum = data.get("min_speed")

        if (
            maximum is not None
            and minimum is not None
            and minimum > maximum
        ):
            self.add_error(
                "min_speed",
                "Minimalne tempo nie może przekraczać "
                "pełnego tempa.",
            )

        return data