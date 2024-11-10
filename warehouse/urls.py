from django.urls import path
from warehouse.views import *


urlpatterns = [
    path('test/', TestView.as_view()),
    path('import_excel/', LoadExcelView.as_view(), name='import_excel'),
    path('load_wz/', LoadWZ.as_view())
]
