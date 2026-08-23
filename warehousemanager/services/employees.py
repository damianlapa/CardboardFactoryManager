import datetime

from warehousemanager.models import Person


def get_employee_list(
    *,
    include_inactive=False,
):
    today = datetime.date.today()

    workers = Person.objects.all()

    if not include_inactive:
        workers = workers.filter(
            job_end__isnull=True
        )

    workers = workers.order_by(
        "last_name",
        "first_name",
    )

    rows = []

    for worker in workers:
        employment_end = (
            worker.job_end
            or today
        )

        employment_days = (
            employment_end
            - worker.job_start
        ).days

        years = employment_days // 365
        months = (
            employment_days % 365
        ) // 30

        if years:
            seniority_label = (
                f"{years} lat {months} mies."
            )
        else:
            seniority_label = (
                f"{months} mies."
            )

        medical_expired = (
            not worker.medical_examination
            or worker.medical_examination < today
        )

        rows.append({
            "worker": worker,

            "seniority": {
                "years": years,
                "months": months,
                "days": employment_days,
                "label": seniority_label,
            },

            "is_active": (
                worker.job_end is None
            ),

            "medical_expired":
                medical_expired,
        })

    return rows