from django.contrib import admin
from django.urls import path, include
from warehousemanager.views import *
from django.conf.urls.static import static


urlpatterns = [
    path('production/', include('production.urls')),

    path('admin/', admin.site.urls, name='admin'),
    path('print-test/', PrintTest.as_view(), name='print-test'),
    path('open-order/<int:order_item_id>/', OpenFile.as_view(), name='open-order'),
    path('format-converter/', FormatConverter.as_view(), name='format-converter'),
    path('add-note/', NoteAdd.as_view(), name='add-note'),
    path('notes/', AllNotes.as_view(), name='notes'),

    path('buyer-add/', AddBuyer.as_view(), name='buyer-add'),
    path('buyers/', BuyersList.as_view(), name='buyers'),
    path('punch-production/', PunchProductions.as_view(), name='punch-production'),
    path('punch-production-add/', PunchProductionAdd.as_view(), name='punch-production-add'),
    path('cardboard-availability/<int:cardboard_id>/', CardboardUsed.as_view(), name='cardboard-used'),
    path('stock-management/', StockManagement.as_view(), name='stock-management'),
    path('announcement/', Announcement.as_view(), name='announcement'),
    path('production-status/', ProductionView.as_view(), name='production-status'),
    path('order-item-details/<int:order_item_id>/', OrderItemDetails.as_view(), name='order-item-details'),
    path('order-item-print/<int:order_item_id>/', OrderItemPrint.as_view(), name='order-item-print'),
    path('gst/', GoogleSheetTest.as_view(), name='gstest'),
    path('prepare-many-gs/', PrepareManySpreadsheetsForm.as_view(), name='prepare-many-gs'),
    path('prepared-gs/', PrepareManySpreadsheets.as_view(), name='prepared-gs'),
    path('scheduled-delivery/', ScheduledDelivery.as_view(), name='scheduled-delivery'),
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
    path('non/', NextOrderNumber.as_view(), name='next-order-number'),
    path('nin/', NextItemNumber.as_view(), name='next-item-number'),
    path('gid/', GetItemDetails.as_view(), name='get-item-details'),
    path('oic/', ChangeOrderState.as_view(), name='order-item-state'),
    path('get-local-var/<str:variable_name>/', GetLocalVar.as_view(), name='get-local-var'),
    path('message-content/<int:message_id>/', MessageContent.as_view(), name='message-content'),
    path('message-read/<int:message_id>/', MessageRead.as_view(), name='message-read'),
]

# clothes
urlpatterns += [
    path('clothes/', ClothesView.as_view(), name='clothes'),
]

# colors
urlpatterns += [
    path('colors/', ColorListView.as_view(), name='colors'),
    path('color/<int:color_id>/', ColorDetail.as_view(), name='color')
]

# contracts
urlpatterns += [
    path('contact-create/', ContractCreate.as_view(), name='contract-create')
]

# deliveries
urlpatterns += [
    path('deliveries-management/', DeliveriesManagement.as_view(), name='deliveries-management'),
    path('delivery/<int:delivery_id>/', DeliveryDetails.as_view(), name='delivery-details'),
    path('delivery-add/', DeliveryAdd.as_view(), name='delivery-add'),
]

# message
urlpatterns += [
    path('messages/', MessageView.as_view(), name='messages')
]

# navigation
urlpatterns += [
    path('', StartPage.as_view(), name='start-page'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('main-page/', MainPageView.as_view(), name='main-page'),
]

# orders
urlpatterns += [
    path('import-order-items/', ImportOrderItems.as_view(), name='import-order-items'),
    path('new-all-orders/', NewAllOrders.as_view(), name='new-all-orders'),
    path('new-order/', NewOrder.as_view(), name='new-order'),
    path('add-items/<int:order_id>/', NewItemAdd.as_view(), name='new-item'),
    path('del-item/<int:order_id>/<int:item_id>/', OrderItemDelete.as_view(), name='delete-item'),
    path('complete-order/', CompleteOrder.as_view(), name='complete-order'),
    path('delete-order/', DeleteOrder.as_view(), name='delete-order'),
]

# palettes
urlpatterns += [
    path('palette-quantities/', PaletteQuantitiesView.as_view(), name='palette-quantities'),
    path('palette-customer/', PaletteCustomerView.as_view(), name='palette-customer'),
    path('palette-customer/<int:customer_id>/', PaletteCustomerDetailView.as_view(), name='palette-customer-detail')
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

# production
'''urlpatterns += [
    path('production/', ProductionProcessListView.as_view(), name='production-list'),
    path('production-create/', ProductionProcessCreate.as_view(), name='production-create')
]'''

# providers
urlpatterns += [
    path('new-provider/', ProviderForm.as_view(), name='new-provider'),
    path('all-providers/', AllProvidersView.as_view(), name='all-providers'),
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

# stats
urlpatterns += [
    path('stats/<str:year>/', StatsView.as_view(), name='stats'),
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
    path('mcp/<int:year>/<int:month>/<int:worker_id>/', MonthlyCardPresence.as_view(), name='mcp')
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
