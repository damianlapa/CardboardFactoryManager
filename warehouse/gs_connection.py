import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime
import requests
import os
import json


def get_data(row_number, year='2024'):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    credentials_json = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
    if credentials_json is None:
        raise EnvironmentError("GOOGLE_CREDENTIALS environment variable not set")
    credentials_info = json.loads(credentials_json)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(credentials_info, scope)

    client = gspread.authorize(creds)
    spreadsheet = client.open("PAKER TEKTURA ZAMÓWIENIA")
    sheet = spreadsheet.worksheet(f"ZAMÓWIENIA {year}")

    return sheet.row_values(row_number)


def get_all(year='2024'):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    credentials_json = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
    if credentials_json is None:
        raise EnvironmentError("GOOGLE_CREDENTIALS environment variable not set")
    credentials_info = json.loads(credentials_json)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(credentials_info, scope)

    client = gspread.authorize(creds)
    spreadsheet = client.open("PAKER TEKTURA ZAMÓWIENIA")
    sheet = spreadsheet.worksheet(f"ZAMÓWIENIA {year}")

    all_values = sheet.get_all_values()

    return all_values


def update_quantity(provider, number, year, value):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    credentials_json = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
    if credentials_json is None:
        raise EnvironmentError("GOOGLE_CREDENTIALS environment variable not set")
    credentials_info = json.loads(credentials_json)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(credentials_info, scope)

    client = gspread.authorize(creds)
    sheet = client.open("PAKER TEKTURA ZAMÓWIENIA").worksheet(f"ZAMÓWIENIA {year}")

    column_a = sheet.col_values(1)
    column_b = sheet.col_values(2)
    column_c = sheet.col_values(3)

    for i in range(1, len(column_a)):
        if column_a[i].lower() == str(provider).lower() and column_b[i] == str(number) and column_c[i] == str(year - 2000):
            row = i + 1
            current_value = sheet.cell(row, 16).value

            if current_value is None:
                current_value = ""
            else:
                if current_value:
                    try:
                        value = int(current_value) + value
                    except Exception as e:
                        pass
                else:
                    pass
            sheet.update_cell(row, 16, value)
            return


def get_rows_numbers(numbers, year, provider, values):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    credentials_json = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
    if credentials_json is None:
        raise EnvironmentError("GOOGLE_CREDENTIALS environment variable not set")
    credentials_info = json.loads(credentials_json)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(credentials_info, scope)

    client = gspread.authorize(creds)
    sheet = client.open("PAKER TEKTURA ZAMÓWIENIA").worksheet(f"ZAMÓWIENIA {year}")

    column_a = sheet.col_values(1)
    column_b = sheet.col_values(2)
    column_c = sheet.col_values(3)

    numbers2 = []
    year = str(year-2000)

    for n in numbers:
        numbers2.append((provider.lower().strip(), str(n), year))

    for i in range(1, len(column_a)):
        row_data = (column_a[i].lower().strip(), str(column_b[i]), str(column_c[i]))
        print(row_data)
        if row_data in numbers2:
            sheet.update_cell(i, 16, values[numbers2.index(row_data)])
