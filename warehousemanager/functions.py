import os
import gspread
import datetime
import random
from django.utils import timezone
from oauth2client.service_account import ServiceAccountCredentials
from warehousemanager.models import SpreadsheetCopy, OrderItem, Order, Punch, UserVisitCounter, Color
from django.core.exceptions import ObjectDoesNotExist

COLORS = ('Red', 'Green', 'Blue', 'Yellow', 'Pink', 'Orange', 'Purple', 'Brown')

def google_key():
    key_parts_tuple = ('-----BEGIN PRIVATE KEY-----', os.environ['PRIVATE_KEY_1'], os.environ['PRIVATE_KEY_2'],
                           os.environ['PRIVATE_KEY_3'],
                           os.environ['PRIVATE_KEY_4'], os.environ['PRIVATE_KEY_5'], os.environ['PRIVATE_KEY_6'],
                           os.environ['PRIVATE_KEY_7'], os.environ['PRIVATE_KEY_8'], os.environ['PRIVATE_KEY_9'],
                           os.environ['PRIVATE_KEY_10'], os.environ['PRIVATE_KEY_11'], os.environ['PRIVATE_KEY_12'],
                           os.environ['PRIVATE_KEY_13'], os.environ['PRIVATE_KEY_14'], os.environ['PRIVATE_KEY_15'],
                           os.environ['PRIVATE_KEY_16'], os.environ['PRIVATE_KEY_17'], os.environ['PRIVATE_KEY_18'],
                           os.environ['PRIVATE_KEY_19'], os.environ['PRIVATE_KEY_20'], os.environ['PRIVATE_KEY_21'],
                           os.environ['PRIVATE_KEY_22'], os.environ['PRIVATE_KEY_23'], os.environ['PRIVATE_KEY_24'],
                           os.environ['PRIVATE_KEY_25'], os.environ['PRIVATE_KEY_26'], '-----END PRIVATE KEY-----')

    key_ = ''

    for part in key_parts_tuple:
        key_ += part
        key_ += '\n'

    return key_


def create_spreadsheet_copy(item_id):
    order_item = OrderItem.objects.get(id=item_id)

    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

    creds_dict = {
        "type": "service_account",
        "project_id": os.environ['PROJECT_ID'],
        "private_key_id": os.environ['PRIVATE_KEY_ID'],
        "private_key": google_key(),
        "client_email": os.environ['CLIENT_EMAIL'],
        "client_id": os.environ['CLIENT_ID'],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": os.environ['CLIENT_CERT_URL']
    }

    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)

    client = gspread.authorize(creds)

    delta_date = order_item.order.date_of_order + datetime.timedelta(days=14)

    date_end = delta_date.strftime('%d.%m.%Y')

    now = datetime.date.today().strftime('%d.%m.%Y')

    # copying

    new_title = f'{order_item}'

    new_gs = client.copy(file_id='1II0BeYj-FuJtWFSkU8mUmU6lMRPqXvWTQw-DXqfzmio', title=new_title,
                         copy_permissions=True)

    sheet_zam = client.open_by_key(new_gs.id)

    sheet = sheet_zam.sheet1

    for s in SpreadsheetCopy.objects.all():
        if timezone.now() > s.created + datetime.timedelta(minutes=30):
            client.del_spreadsheet(s.gs_id)
            s.delete()

    SpreadsheetCopy.objects.create(gs_id=new_gs.id)

    # quantity
    sheet.update_cell(18, 21, order_item.ordered_quantity)

    # order realisation
    sheet.update_cell(12, 16, date_end)

    # order preparing date
    sheet.update_cell(15, 9, now)

    # order name
    if order_item.name:
        sheet.update_cell(12, 28, order_item.name)
    else:
        sheet.update_cell(12, 28, '')

    # order cardboard
    sheet.update_cell(18, 16,
                      f'{order_item.cardboard_type}{order_item.cardboard_weight}{order_item.cardboard_additional_info}')

    buyer_list = order_item.buyer.all()

    buyer = ''

    for b in buyer_list:
        if buyer != '':
            buyer += ', '
        buyer += str(b.shortcut)

    machine = ''

    if order_item.sort in ('201', '202', '203'):
        machine = 'SLO'
    elif order_item.sort == 'SZTANCA':
        machine = 'TYG'
    elif order_item.sort == 'PRZEKLADKA':
        machine = 'MAG'
        if order_item.dimension_one != order_item.format_width:
            machine = 'KRA'
        elif order_item.dimension_two != order_item.format_height:
            machine = 'KRA'

    punch_id = ''

    if order_item.sort == 'SZTANCA':
        punches = Punch.objects.filter(dimension_one=order_item.dimension_one).filter(
            dimension_two=order_item.dimension_two).filter(dimension_three=order_item.dimension_three)
        if punches.count() > 0:
            punch_id = ''
            for p in punches:
                if punch_id != '':
                    punch_id += ', '
                punch_id += p.punch_name()

    sheet.update_cell(12, 21, machine)

    sheet.update_cell(20, 6, punch_id)

    sheet.update_cell(18, 24, f'{order_item.format_width}x{order_item.format_height}')

    sheet.update_cell(17, 1, order_item.dimension_one)

    sheet.update_cell(17, 6, order_item.dimension_two)

    if order_item.dimension_three:
        sheet.update_cell(17, 11, order_item.dimension_three)
    else:
        sheet.update_cell(17, 11, '')

    provider_lower = str(order_item.order.provider).lower()

    if provider_lower == 'convert':
        prov_shortcut = 'CN'
    elif provider_lower == 'aquila':
        prov_shortcut = 'AQ'
    elif provider_lower == 'werner':
        prov_shortcut = 'WER'
    else:
        prov_shortcut = 'NN'

    #
    sheet.update_cell(6, 11,
                      f'{prov_shortcut} {order_item.order.order_provider_number}/{order_item.item_number} {buyer}')

    return (new_gs.id)


def visit_counter(user, page):
    if user.is_authenticated:
        try:
            visit = UserVisitCounter.objects.get(user=user, page=page)
            visit.counter += 1
            visit.save()
        except ObjectDoesNotExist:
            new_visit = UserVisitCounter.objects.create(user=user, page=page)
            new_visit.save()


def add_random_color(num):
    for _ in range(num):
        name = str(random.randint(0, 3)) + str(random.randint(0, 9)) + str(random.randint(0, 9)) + ' U'
        red = random.randint(0, 255)
        green = random.randint(0, 255)
        blue = random.randint(0, 255)
        Color.objects.create(name=random.choice(COLORS), number=name, red=red, green=green, blue=blue)


def change_minutes_to_hours(minutes):
    return f'{minutes // 60}:{minutes % 60}' if minutes % 60 > 9 else f'{minutes // 60}:0{minutes % 60}'
