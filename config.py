from os import environ

API_ID = int(environ.get("API_ID", "37502609"))
API_HASH = environ.get("API_HASH", "cd4e39a4344aad8946b904292abbdf14")
BOT_TOKEN = environ.get("BOT_TOKEN", "8611961334:AAGAdtZtIqo9u083Wo_eEnAgcGJKCmYoXFk")

LOG_CHANNEL = int(environ.get("LOG_CHANNEL", "-1003835007743"))

# Supports one admin ID or comma-separated IDs: 123,456,789
_raw_admins = environ.get("ADMINS", "8363262755")
ADMINS = [int(x.strip()) for x in _raw_admins.split(",") if x.strip().lstrip("-").isdigit()]
if not ADMINS:
    ADMINS = [0]

DB_URI = environ.get("DB_URI", "mongodb+srv://nnr4lxwdkasdev_db_user:mwsnTzZuTX8b7Kou@cluster0.76bddsl.mongodb.net")
DB_NAME = environ.get("DB_NAME", "vjjoinrequetbot")
NEW_REQ_MODE = environ.get("NEW_REQ_MODE", "true").strip().lower() in ("1", "true", "yes", "on")
