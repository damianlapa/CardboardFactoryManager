import xml.etree.ElementTree as ET

from django.http import HttpResponse
from django.contrib.auth.decorators import login_required


@login_required
def edi_test_xml(request):
    namespace = "http://vpk.be/AQUILA/SalesOrder"

    root = ET.Element(
        f"{{{namespace}}}SalesOrder_aquila"
    )

    header = ET.SubElement(root, "Header")

    ET.SubElement(header, "DeliveryDate").text = "20261016"
    ET.SubElement(header, "CustomerPurchaseOrder").text = "TEST"
    ET.SubElement(header, "ShipTo").text = "83867"

    cumulative = ET.SubElement(header, "CumulativeQuantity")
    cumulative.set("UnitOfMeasure", "")

    ET.SubElement(header, "CustomerNumber").text = "38465"
    ET.SubElement(header, "LabelType")

    rate = ET.SubElement(header, "Rate")
    rate.set("UnitOfMeasure", "")

    items = ET.SubElement(root, "Items")
    item = ET.SubElement(items, "Item")

    ET.SubElement(item, "CustomerReferenceLineNumber").text = "1"
    ET.SubElement(item, "MaterialNumber").text = "sheets"
    ET.SubElement(item, "BoardGrade").text = "5BC640A1"
    ET.SubElement(item, "MaterialDescription").text = "(1600x800)"

    price = ET.SubElement(item, "Price")
    price.set("Currency", "PLN")
    price.text = "1.100"

    ET.SubElement(item, "Remark")
    ET.SubElement(item, "LabelType")
    ET.SubElement(item, "MaxOverDeliveryTotal")
    ET.SubElement(item, "MaxUnderDeliveryTotal")

    ET.SubElement(item, "MaterialDescription").text = "5BC640A1,1600x800"

    sheet = ET.SubElement(item, "Sheet")
    ET.SubElement(sheet, "WidthX").text = "800"

    ET.SubElement(item, "WidthY").text = "0"
    ET.SubElement(item, "Length").text = "1600"
    ET.SubElement(item, "QuantityPce").text = "400"
    ET.SubElement(item, "QuantityM2").text = "512.000"

    scores = ET.SubElement(item, "Scores")
    scores.set("NumberOfScores", "0")
    scores.set("Scored", "800")

    ET.SubElement(item, "score_type").text = "0"

    ET.SubElement(item, "WebshopComment").text = "TEST"
    ET.SubElement(item, "RequestedDelDate").text = "20261016"
    ET.SubElement(item, "ProposedDelDate").text = "20261016"

    xml_body = ET.tostring(
        root,
        encoding="utf-8",
        xml_declaration=True,
    )

    return HttpResponse(
        xml_body,
        content_type="application/xml; charset=utf-8",
    )