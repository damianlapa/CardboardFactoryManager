from django.views import View
from django.shortcuts import render
from warehousemanager.models import Person
import datetime


class EmployeeListView(View):
    template_name = "whm/employees/employee_list.html"

    def get(self, request):
        show_all = request.GET.get("all") == "1"

        workers_qs = Person.objects.all()

        if not show_all:
            workers_qs = workers_qs.filter(job_end__isnull=True)

        workers = []
        today = datetime.date.today()

        for w in workers_qs:
            end = w.job_end or today
            delta = end - w.job_start
            years = delta.days // 365
            months = (delta.days % 365) // 30

            workers.append({
                "worker": w,
                "seniority": f"{years} lat {months} mies." if years else f"{months} mies.",
                "status": "Aktywny" if not w.job_end else "Nieaktywny",
                "medical_expired": not w.medical_examination or w.medical_examination < today,
            })

        return render(request, self.template_name, {
            "workers": workers,
            "show_all": show_all,
        })