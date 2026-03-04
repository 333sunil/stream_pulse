from dynaconf import Dynaconf

settings = Dynaconf(
    settings_files=["config/settings.toml", "config/.secrets.toml"],
    environments=True,
    load_dotenv=True,
)

# Safely get DB credentials and connection info
db_user = settings.get("DB_USER", "test")
db_password = settings.get("DB_PASSWORD", "test")
db_host = settings.get("DB_HOST", "localhost")
db_port = settings.get("DB_PORT", "5432")
db_name = settings.get("DB_NAME", "streampulse")

# Construct DB_URL
settings.DB_URL = (
    f"postgresql+asyncpg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
)
