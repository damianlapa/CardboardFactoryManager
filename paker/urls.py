"""paker1 URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from warehousemanager.views import *
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    # path('', index, name='index'),
    path('orders/', Orders.as_view(), name='orders'),
    path('order/<int:order_id>', OrdersDetails.as_view(), name='order-details'),
    path('orders-details/', AllOrdersDetails.as_view(), name='all-orders-details'),
    path('new-order/', NewOrder.as_view(), name='new-order'),
    path('uncompleted-orders', UncompletedOrders.as_view(), name='uncompleted-orders'),
    path('non/', NextOrderNumber.as_view(), name='next-order-number'),
    path('create-new-order/', NewOrderAdd.as_view(), name='new-order-create'),
    path('new-provider/', ProviderForm.as_view(), name='new-provider'),
    path('add-items/<int:order_id>', NewItemAdd.as_view(), name='new-item'),
    path('nin/', NextItemNumber.as_view(), name='next-tem-number'),
    path('del-item/<int:order_id>/<int:item_id>', OrderItemDelete.as_view(), name='delete-item'),
    path('complete-order/', CompleteOrder.as_view(), name='complete-order'),
    path('delete-order/', DeleteOrder.as_view(), name='delete-order'),
    path('gid/', GetItemDetails.as_view(), name='get-item-details'),
    path('print-test/', PrintTest.as_view(), name='print-test'),
    path('open-order/<int:order_item_id>/', OpenFile.as_view(), name='open-order'),
    path('new-all-orders/', NewAllOrders.as_view(), name='new-all-orders'),
    path('', StartPage.as_view(), name='start-page'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('manage/', ManageView.as_view(), name='manage'),
    path('all-providers/', AllProvidersView.as_view(), name='all-providers'),
    path('format-converter', FormatConverter.as_view(), name='format-converter'),
    path('deliveries-management', DeliveriesManagement.as_view(), name='deliveries-management'),
    path('delivery/<int:delivery_id>', DeliveryDetails.as_view(), name='delivery-details'),
    path('delivery-add/', DeliveryAdd.as_view(), name='delivery-add'),
    path('add-note/', NoteAdd.as_view(), name='add-note'),
    path('notes/', AllNotes.as_view(), name='notes'),
    path('absences-list/', AbsencesList.as_view(), name='absence-list'),
    path('absences/', AbsencesAndHolidays.as_view(), name='absences'),
    path('get-local-var/<str:variable_name>/', GetLocalVar.as_view(), name='get-local-var'),
    path('add-absence/', AbsenceAdd.as_view(), name='add-absence'),
    path('punches/', PunchesList.as_view(), name='punches'),
    path('punch-add/', PunchAdd.as_view(), name='punch-add'),
    path('punch/<str:punch_id>', PunchDetails.as_view(), name='punch-details'),
    path('punch-edit/<int:punch_id>', PunchEdit.as_view(), name='punch-edit'),
    path('punch-delete/<int:punch_id>', PunchDelete.as_view(), name='punch-delete'),
    path('buyer-add/', AddBuyer.as_view(), name='buyer-add'),
    path('buyers/', BuyersList.as_view(), name='buyers'),
    path('punch-production/', PunchProductions.as_view(), name='punch-production'),
    path('punch-production-add/', PunchProductionAdd.as_view(), name='punch-production-add'),
    path('cardboard-availability/<int:cardboard_id>', CardboardUsed.as_view(), name='cardboard-used'),
    path('stock-management/', StockManagement.as_view(), name='stock-management'),
    path('announcement/', Announcement.as_view(), name='announcement'),
    path('oic/', ChangeOrderState.as_view(), name='order-item-state'),
    path('production-status/', ProductionView.as_view(), name='production-status'),
    path('order-item-details/<int:order_item_id>/', OrderItemDetails.as_view(), name='order-item-details'),
    path('order-item-print/<int:order_item_id>/', OrderItemPrint.as_view(), name='order-item-print'),
    path('gst/', GoogleSheetTest.as_view(), name='gstest'),
    path('import-order-items/', ImportOrderItems.as_view(), name='import-order-items'),
    path('prepare-many-gs/', PrepareManySpreadsheetsForm.as_view(), name='prepare-many-gs'),
    path('prepared-gs/', PrepareManySpreadsheets.as_view(), name='prepared-gs'),
    path('scheduled-delivery/', ScheduledDelivery.as_view(), name='scheduled-delivery'),
    path('polymers/', PhotoPolymers.as_view(), name='photopolymers')
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
