import requests
import urllib3

from django.conf import settings
from django.core.exceptions import ValidationError


# ============================================================
# KONFIGURACJA JASSBOARD
# ============================================================

BASE_URL = getattr(
    settings,
    "JASSBOARD_BASE_URL",
    "https://sktest.jassboard.com",
)

EMAIL = settings.JASSBOARD_EMAIL
PASSWORD = settings.JASSBOARD_PASSWORD
address_erp_id = settings.JASSBOARD_ADDRESS_ERP_ID

# Na środowisku testowym JassBoard występuje obecnie
# problem z łańcuchem certyfikatu SSL.
VERIFY_SSL = getattr(
    settings,
    "JASSBOARD_VERIFY_SSL",
    False,
)

if not VERIFY_SSL:
    urllib3.disable_warnings(
        urllib3.exceptions.InsecureRequestWarning
    )


# ============================================================
# KLIENT API
# ============================================================

class JassBoardClient:

    def __init__(
        self,
        *,
        email=None,
        password=None,
    ):
        self.email = email or EMAIL
        self.password = password or PASSWORD

        self.token = None

        self.session = requests.Session()


    # ========================================================
    # REQUEST
    # ========================================================

    def _url(self, path):
        return (
            f"{BASE_URL.rstrip('/')}/"
            f"{path.lstrip('/')}"
        )


    def _auth_headers(self):
        if not self.token:
            self.login()

        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
        }


    def _request(
        self,
        method,
        path,
        *,
        authenticated=True,
        **kwargs,
    ):
        headers = kwargs.pop(
            "headers",
            {},
        )

        if authenticated:
            headers.update(
                self._auth_headers()
            )

        try:
            response = self.session.request(
                method=method,
                url=self._url(path),
                headers=headers,
                verify=VERIFY_SSL,
                timeout=30,
                **kwargs,
            )

        except requests.RequestException as exc:
            raise ValidationError(
                f"Błąd połączenia z JassBoard: {exc}"
            ) from exc

        if not response.ok:
            raise ValidationError(
                (
                    "JassBoard zwrócił błąd. "
                    f"HTTP {response.status_code}: "
                    f"{response.text}"
                )
            )

        try:
            return response.json()

        except ValueError:
            raise ValidationError(
                (
                    "JassBoard zwrócił odpowiedź "
                    "w nieoczekiwanym formacie: "
                    f"{response.text}"
                )
            )


    # ========================================================
    # LOGOWANIE
    # ========================================================

    def login(self):

        data = self._request(
            "POST",
            "/Api/Identity/Login",
            authenticated=False,
            data={
                "Email": self.email,
                "Password": self.password,
            },
            headers={
                "Content-Type":
                    "application/x-www-form-urlencoded",
            },
        )

        token = data.get("token")

        if not token:
            raise ValidationError(
                (
                    "JassBoard nie zwrócił tokenu. "
                    f"Odpowiedź: {data}"
                )
            )

        self.token = token

        return token


    # ========================================================
    # SŁOWNIKI
    # ========================================================

    def get_types(self):

        return self._request(
            "GET",
            "/Api/Dictionary/GetTypes",
        )


    def get_addresses(self):

        return self._request(
            "GET",
            "/Api/Dictionary/GetAddresses",
        )

    def get_compositions_tf(self, board_type):

        if board_type not in ("TF2", "TF35"):
            raise ValidationError(
                "Typ tektury musi być TF2 albo TF35."
            )

        return self._request(
            "GET",
            "/Api/Dictionary/GetCompositionTf",
            params={
                "type": board_type,
            },
        )


    def get_calendar(self):

        return self._request(
            "GET",
            "/Api/Dictionary/GetCalendar",
        )


    # ========================================================
    # ZAMÓWIENIA
    # ========================================================

    def add_order(self, payload):

        return self._request(
            "POST",
            "/Api/Orders/Add",
            json=payload,
            headers={
                "Content-Type":
                    "application/json",
            },
        )

    def get_order(self, order_id):

        return self._request(
            "GET",
            "/Api/Orders/Get",
            params={
                "id": order_id,
            },
        )
