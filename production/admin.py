from django.contrib import admin
from production.models import *

admin.site.register(ProductionOrder)
admin.site.register(ProductionUnit)
admin.site.register(WorkStation)
admin.site.register(WeeklyPlan)
admin.site.register(ProductionTask)
