import secrets
import sys
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent
DIRECTORIO_VAR = BASE_DIR / "var"
DIRECTORIO_VAR.mkdir(exist_ok=True)

EJECUTANDO_PRUEBAS = "test" in sys.argv


def _leer_env(ruta: Path) -> dict[str, str]:
    """Formato CLAVE=valor; ignora líneas vacías y comentarios. Sin el archivo devuelve {}."""
    valores = {}
    if ruta.is_file():
        for linea in ruta.read_text(encoding="utf-8").splitlines():
            linea = linea.strip()
            if linea and not linea.startswith("#") and "=" in linea:
                clave, valor = linea.split("=", 1)
                valores[clave.strip()] = valor.strip().strip("\"'")
    return valores


ENTORNO = _leer_env(BASE_DIR / ".env")

SECRET_KEY = ENTORNO.get("SECRET_KEY", "")
if not SECRET_KEY:
    if not EJECUTANDO_PRUEBAS:
        raise ImproperlyConfigured("Falta SECRET_KEY: copia .env.example a .env (ver README).")
    # Las pruebas no deben depender de .env; una clave al azar por ejecución basta.
    SECRET_KEY = secrets.token_urlsafe(50)
DEBUG = ENTORNO.get("DEBUG", "0").lower() in {"1", "true", "si", "sí"}
# RNF-02: con DEBUG se acepta cualquier host para probar desde un teléfono en la misma red.
ALLOWED_HOSTS = ["*"] if DEBUG else ENTORNO.get("ALLOWED_HOSTS", "localhost").split(",")

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "subastas",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "subastas.middleware.ProcesoDelTiempoMiddleware",
    "subastas.middleware.CuentaActivaMiddleware",
    "subastas.middleware.ErroresDeNegocioMiddleware",
]

ROOT_URLCONF = "casa_subastas.urls"
WSGI_APPLICATION = "casa_subastas.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "subastas.contexto.sesion_actual",
            ],
        },
    },
]

# SQLite ignora select_for_update. Con IMMEDIATE cada transacción toma el bloqueo
# de escritura al empezar, y dos pujas simultáneas se atienden una tras otra.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
        "OPTIONS": {"transaction_mode": "IMMEDIATE", "timeout": 20},
        # En archivo y no en memoria: la prueba de concurrencia abre dos conexiones.
        "TEST": {"NAME": DIRECTORIO_VAR / "pruebas.sqlite3"},
    }
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "subastas.Usuario"
LOGIN_URL = "entrar"
if EJECUTANDO_PRUEBAS:
    # MD5 solo en pruebas, para que no tarden.
    PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

LANGUAGE_CODE = "es-mx"
TIME_ZONE = "America/Mexico_City"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# Para usar el servicio real de otro equipo se cambia solo su línea.
INTEGRACIONES = {
    "pagos": "subastas.integraciones.simulados.PagosSimulado",
    "valuador": "subastas.integraciones.simulados.ValuadorSimulado",
    "logistica": "subastas.integraciones.simulados.LogisticaSimulada",
    "identidad": "subastas.integraciones.simulados.IdentidadSimulada",
    "codigo_movil": "subastas.integraciones.simulados.CodigoMovilSimulado",
    "correo": "subastas.integraciones.simulados.CorreoSimulado",
}
BANDEJA_SIMULADA = DIRECTORIO_VAR / "bandeja_simulada.jsonl"

RELOJ = "subastas.reloj.RelojDemo" if DEBUG and not EJECUTANDO_PRUEBAS else "subastas.reloj.RelojSistema"
RELOJ_DEMO_ARCHIVO = DIRECTORIO_VAR / "reloj_demo.json"
