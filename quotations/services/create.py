from django.db import transaction

from ..models import Quotation, QuotationCustomer


@transaction.atomic
def create_quotation(*, customer, new_customer_name, date):
    """Create a quotation from validated QuotationCreateForm data."""
    if not customer:
        customer = QuotationCustomer.objects.create(name=new_customer_name)
    return Quotation.objects.create(customer=customer, date=date)
