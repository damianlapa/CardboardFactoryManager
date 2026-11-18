from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from ..models import (
    QuotationProcessProfile,
    QuotationProcessFluteRule,
)
from ..process_forms import (
    ProcessProfileForm,
    ProcessFluteRuleForm,
)


PROFILE_CODE = "ROTATION_NO_PRINT"

FLUTES = ("B", "C", "E", "EB", "BC")


def get_process_settings_context(data=None):
    profile = (
        QuotationProcessProfile.objects
        .prefetch_related("flute_rules")
        .filter(code=PROFILE_CODE)
        .first()
    )

    existing = (
        {
            rule.flute: rule
            for rule in profile.flute_rules.all()
        }
        if profile
        else {}
    )

    profile_form = ProcessProfileForm(
        data=data,
        instance=(
            profile
            or QuotationProcessProfile(code=PROFILE_CODE)
        ),
        prefix="profile",
    )

    rows = []

    for flute in FLUTES:
        fast = flute in ("B", "C", "E")

        rule = existing.get(flute)

        if rule is None:
            rule = QuotationProcessFluteRule(
                flute=flute,
                first_batch_minutes=10 if fast else 15,
                max_speed=4000 if fast else 2000,
                min_speed=1000 if fast else 500,
            )

        rows.append({
            "flute": flute,
            "form": ProcessFluteRuleForm(
                data=data,
                instance=rule,
                prefix=f"flute-{flute}",
            ),
        })

    return {
        "profile_form": profile_form,
        "rows": rows,
    }


@transaction.atomic
def save_process_settings(context):
    valid = [
        context["profile_form"].is_valid(),
    ] + [
        row["form"].is_valid()
        for row in context["rows"]
    ]

    if not all(valid):
        return False

    profile, _ = (
        QuotationProcessProfile.objects.update_or_create(
            code=PROFILE_CODE,
            defaults=context["profile_form"].cleaned_data,
        )
    )

    for row in context["rows"]:
        QuotationProcessFluteRule.objects.update_or_create(
            profile=profile,
            flute=row["flute"],
            defaults=row["form"].cleaned_data,
        )

    return True


def calculate_rotation_time(
    *,
    quantity,
    sheet_width,
    sheet_length,
    flute,
):
    """
    Oblicza czas rotacji bez nadruku.

    quantity — liczba arkuszy przechodzących przez maszynę.
    sheet_width i sheet_length — wymiary arkusza w mm.
    """
    try:
        quantity, width, length = (
            Decimal(str(value))
            for value in (
                quantity,
                sheet_width,
                sheet_length,
            )
        )

        if any(
            not value.is_finite()
            or value <= 0
            or value != value.to_integral_value()
            for value in (quantity, width, length)
        ):
            raise ValueError

    except (ValueError, ArithmeticError):
        raise ValidationError(
            "Podaj dodatnią całkowitą liczbę arkuszy "
            "i wymiary arkusza w mm."
        )

    profile = (
        QuotationProcessProfile.objects
        .filter(code=PROFILE_CODE)
        .first()
    )

    if not profile:
        raise ValidationError(
            "Najpierw zapisz ustawienia rotacji "
            "bez nadruku."
        )

    rule = profile.flute_rules.filter(
        flute=flute.strip().upper(),
    ).first()

    if not rule:
        raise ValidationError(
            "Brak ustawień rotacji dla wybranej fali."
        )

    if quantity < profile.first_batch_quantity:
        raise ValidationError(
            "Nakład jest mniejszy od pierwszej partii "
            "skonfigurowanej w ustawieniach."
        )

    area = width * length / Decimal("1000000")

    if area <= profile.full_speed_area:
        speed = rule.max_speed

    elif area >= profile.min_speed_area:
        speed = rule.min_speed

    else:
        # Liniowy spadek wydajności między progami.
        fraction = (
            (area - profile.full_speed_area)
            / (
                profile.min_speed_area
                - profile.full_speed_area
            )
        )

        speed = (
            rule.max_speed
            - (
                rule.max_speed - rule.min_speed
            ) * fraction
        )

    remaining = (
        quantity - profile.first_batch_quantity
    )

    # Pierwsza partia ma osobny czas.
    # Pozostały nakład jest liczony według wydajności.
    run_minutes = (
        rule.first_batch_minutes
        + remaining / speed * Decimal("60")
    )

    total_minutes = (
        profile.setup_minutes + run_minutes
    )

    # Roboczogodziny uwzględniają obsadę.
    person_hours = (
        profile.setup_minutes * profile.setup_workers
        + run_minutes * profile.run_workers
    ) / Decimal("60")

    return {
        "area_m2": area,
        "speed": speed,
        "setup_minutes": profile.setup_minutes,
        "run_minutes": run_minutes,
        "total_minutes": total_minutes,
        "machine_hours": total_minutes / Decimal("60"),
        "person_hours": person_hours,
        "setup_workers": profile.setup_workers,
        "run_workers": profile.run_workers,
    }