from django.contrib import admin
from django.urls import path, include
from warehousemanager.views import *
from django.conf.urls.static import static


urlpatterns = [
    path('production/', include('production.urls')),
    # path('orders/', include('orders.urls')),
    path('deliveries/', include('deliveries.urls')),
    path('whm/', include('warehousemanager.urls')),
    path('warehouse/', include('warehouse.urls', namespace='warehouse')),
    path("maintenance/", include("maintenance.urls")),

    path('admin/', admin.site.urls, name='admin'),

    path('buyer-add/', AddBuyer.as_view(), name='buyer-add'),
    path('buyers/', BuyersList.as_view(), name='buyers'),
]

# absences
urlpatterns += [
    path('absences-list/', AbsencesList.as_view(), name='absence-list'),
    path('absences/', AbsencesAndHolidays.as_view(), name='absences'),
    path('add-absence/', AbsenceAdd.as_view(), name='add-absence'),
    path('person-absences/<int:person_id>/', PersonAbsences.as_view(), name='person-absences'),
    path('absence-delete/', AbsenceDelete.as_view(), name='absence-delete'),
]

# ajax views
urlpatterns += [
    path('get-local-var/<str:variable_name>/', GetLocalVar.as_view(), name='get-local-var'),
]

# colors
urlpatterns += [
    path('colors/', ColorListView.as_view(), name='colors'),
    path('color/<int:color_id>/', ColorDetail.as_view(), name='color'),
    path('colors/refresh/', ColorRefresh.as_view(), name='color-refresh'),
    path('colors/bucket/<int:bucket_id>/', BucketDetail.as_view(), name='bucket-details'),
    path('colors/bucket/<int:bucket_id>/qrcode/', BucketQRCode.as_view(), name='bucketQRcode')
]

# contracts
urlpatterns += [
    path('contact-create/', ContractCreate.as_view(), name='contract-create')
]


# navigation
urlpatterns += [
    path('', StartPage.as_view(), name='start-page'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('login/', LoginView.as_view(), name='login'),
    path('main-page/', MainPageView.as_view(), name='main-page'),
]

# palettes
urlpatterns += [
    path('palette-quantities/', PaletteQuantitiesView.as_view(), name='palette-quantities'),
]
# persons
urlpatterns += [
    path('persons/', PersonListView.as_view(), name='persons'),
    path('person/<int:person_id>/', PersonDetailView.as_view(), name='person-details')
]

# polymers
urlpatterns += [
    path('polymers/', PhotoPolymers.as_view(), name='photopolymers'),
    path('polymer/<int:polymer_id>/', PhotoPolymerDetail.as_view(), name='polymer-details'),
    path('polymer-create/', PolymerCreate.as_view(), name='polymer-create'),
    path('polymer-update/<int:pk>/', PolymerUpdate.as_view(), name='polymer-update'),
    path('polymer-delete/<int:pk>/', PolymerDelete.as_view(), name='polymer-delete'),
]

# punches
urlpatterns += [
    path('punches/', PunchesList.as_view(), name='punches'),
    path('punch-add/', PunchAdd.as_view(), name='punch-add'),
    path('punch/<str:punch_id>/', PunchDetails.as_view(), name='punch-details'),
    path('punch-edit/<int:punch_id>/', PunchEdit.as_view(), name='punch-edit'),
    path('punch-delete/<int:punch_id>/', PunchDelete.as_view(), name='punch-delete'),
]

# reminders
urlpatterns += [
    path('reminders/', ReminderListView.as_view(), name='reminders'),
    path('reminder/<int:reminder_id>/', ReminderDetailsView.as_view(), name='reminder-details'),
    path('reminder-delete/<int:reminder_id>/', ReminderDeleteView.as_view(), name='reminder-delete')
]

# services
urlpatterns += [
    path('services/', ServiceListView.as_view(), name='services'),
    path('service/<int:pk>/', ServiceDetailView.as_view(), name='service-details'),
    path('service-create/', ServiceCreate.as_view(), name='service-create'),
    path('service-update/<int:pk>/', ServiceUpdate.as_view(), name='service-update'),
    path('service-delete/<int:pk>/', ServiceDelete.as_view(), name='service-delete'),
]

# vacations
urlpatterns += [
    path('vacations/', AvailableVacation.as_view(), name='vacations'),
    path('persons-vacations/<int:person_id>/', PersonsVacations.as_view(), name='persons-vacations')
]

# profile
urlpatterns += [
    path('profile/', ProfileView.as_view(), name='profile')
]

# monthly card presence
urlpatterns += [
    path('mcp/<int:year>/<int:month>/<int:worker_id>/', MonthlyCardPresence.as_view(), name='mcp'),
    path('mcpa/<int:year>/<int:month>/', MonthlyCardPresenceAll.as_view(), name='mcpa')
]

# work reminders
urlpatterns += [
    path('workreminders/', WorkRemindersView.as_view(), name='workreminders'),
    path('workreminders/add/', WorkReminderAdd.as_view(), name='workreminders-add')
]

urlpatterns += [
    path('gluernumbers/', GluerNumberView.as_view(), name='gluernumbers'),
    path('gluernumberget/', GluerNumberGet.as_view()),
    path('polymernumberget/', PolymerNumberGet.as_view()),
    path('punchnumberget/', PunchNumberGet.as_view()),
]

# print polymers
urlpatterns += [
    path('print-polymers/', PrintPolymers.as_view(), name='print-polymers')
]

urlpatterns += [
    path('active_hours/', ActiveHours.as_view(), name='active-hours')
]

urlpatterns += [
    path('wwtest/', WorkersVacationsTest.as_view())
]

urlpatterns += [
    path('add-note/', NoteAdd.as_view(), name='add-note'),
    path('notes/', AllNotes.as_view(), name='notes'),
    path('note-details/<int:note_id>/', NoteDetailsView.as_view(), name='note-details'),
    path('note-delete/<int:note_id>/', NoteDeleteView.as_view(), name='note-delete'),
]
