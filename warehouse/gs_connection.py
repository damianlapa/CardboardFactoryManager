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
