"""Run: python manage.py test warehouse.test_shipment_item_quantities"""
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import patch

from django.core.exceptions import PermissionDenied
from django.test import RequestFactory, SimpleTestCase

from warehouse.shipment_item_quantity_views import ShipmentItemQuantityForm, ShipmentItemQuantityListView

MODULE = "warehouse.shipment_item_quantity_views"


class ShipmentItemQuantityTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = SimpleNamespace(is_authenticated=True, has_perms=lambda permissions: True)
        self.unit = SimpleNamespace(pk=12, quantity=1, palette_quantity=3, order_id=4, product_id=5, palette_id=6)
        self.item = SimpleNamespace(pk=7, shipment_unit_id=12)

    def request(self, quantity="600", expected="1"):
        request = self.factory.post("/shipment-items/quantities/", {
            "item_id": "7", "quantity": quantity, "expected_quantity": expected,
        }, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        request.user = self.user
        return request

    def test_form_rejects_bad_quantities(self):
        for value in ("", "0", "-1", "1.5", "abc", "2147483648"):
            with self.subTest(value=value):
                self.assertFalse(ShipmentItemQuantityForm({"item_id": "7", "expected_quantity": "1", "quantity": value}).is_valid())

    def test_missing_expected_value_is_rejected(self):
        self.assertFalse(ShipmentItemQuantityForm({"item_id": "7", "quantity": "600"}).is_valid())

    def run_post(self, request):
        with patch(MODULE + ".transaction.atomic", return_value=nullcontext()), \
             patch(MODULE + ".get_object_or_404", side_effect=[self.item, self.unit]), \
             patch(MODULE + ".ShipmentUnit.objects.filter") as unit_filter, \
             patch(MODULE + ".ShipmentUnitHistory.objects.create") as history:
            response = ShipmentItemQuantityListView.as_view()(request)
        return response, unit_filter, history

    def test_changes_only_one_units_pieces_and_records_old_values(self):
        response, unit_filter, history = self.run_post(self.request())
        self.assertEqual(response.status_code, 200)
        unit_filter.assert_called_once_with(pk=12)
        unit_filter.return_value.update.assert_called_once_with(quantity=600)
        self.assertEqual(history.call_args.kwargs["quantity"], 1)
        self.assertEqual(history.call_args.kwargs["palette_quantity"], 3)
        self.assertIs(history.call_args.kwargs["changed_by"], self.user)
        self.assertEqual(self.unit.palette_quantity, 3)

    def test_same_value_does_not_write_history_or_update(self):
        response, unit_filter, history = self.run_post(self.request(quantity="1"))
        self.assertEqual(response.status_code, 200)
        unit_filter.assert_not_called()
        history.assert_not_called()

    def test_stale_value_does_not_overwrite(self):
        self.unit.quantity = 450
        response, unit_filter, history = self.run_post(self.request())
        self.assertEqual(response.status_code, 409)
        unit_filter.assert_not_called()
        history.assert_not_called()

    def test_old_zero_can_be_corrected(self):
        self.unit.quantity = 0
        response, unit_filter, history = self.run_post(self.request(expected="0"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(history.call_args.kwargs["quantity"], 0)
        unit_filter.return_value.update.assert_called_once_with(quantity=600)

    def test_invalid_submission_does_not_touch_database(self):
        with patch(MODULE + ".get_object_or_404") as lookup:
            response = ShipmentItemQuantityListView.as_view()(self.request(quantity="0"))
        self.assertEqual(response.status_code, 400)
        lookup.assert_not_called()

    def test_permission_is_required(self):
        self.user.has_perms = lambda permissions: False
        with self.assertRaises(PermissionDenied):
            ShipmentItemQuantityListView.as_view()(self.request())
