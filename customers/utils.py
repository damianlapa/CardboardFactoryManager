import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
#
#
# GOOGLE_SHEETS_CREDENTIALS = {
#         "type": os.environ['PE_TYPE'],
#         "project_id": os.environ['PE_PROJECT_ID'],
#         "private_key_id": os.environ['PE_PRIVATE_KEY_ID'],
#         "private_key": os.environ['PE_PRIVATE_KEY'].replace('\\n', '\n'),
#         "client_email": os.environ['PE_CLIENT_EMAIL'],
#         "client_id": os.environ['PE_CLIENT_ID'],
#         "auth_uri": os.environ['PE_AUTH_URI'],
#         "token_uri": os.environ['PE_TOKEN_URI'],
#         "auth_provider_x509_cert_url": os.environ['PE_AUTH_PROVIDER_X509_CERT_URL'],
#         "client_x509_cert_url": os.environ['PE_CLIENT_X509_CERT_URL'],
#     }
#
#
# def get_data(year='2024'):
#     scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
#     creds = ServiceAccountCredentials.from_json_keyfile_dict(GOOGLE_SHEETS_CREDENTIALS, scope)
#     client = gspread.authorize(creds)
#     spreadsheet = client.open("PAKER TEKTURA ZAMÓWIENIA")
#     sheet = spreadsheet.worksheet(f"ZAMÓWIENIA {year}")
#
#     return sheet.get_all_values()
