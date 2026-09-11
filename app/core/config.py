import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(os.path.join(BASE_DIR, ".env"))

class Settings:
    PROJECT_NAME: str = "ADT-System - PT Anugrah Djaya Tunggal"
    BASE_DIR: Path = BASE_DIR
    PDF_OUTPUT_DIR: Path = BASE_DIR / "generated_pdfs"
    PO_UPLOAD_DIR: Path = BASE_DIR / "uploaded_pos"
    STATIC_DIR: Path = BASE_DIR / "app" / "static"
    TEMPLATES_DIR: Path = BASE_DIR / "app" / "templates"
    LOGO_PATH: Path = STATIC_DIR / "logo.png"

    # Database
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "3306"))
    DB_USER: str = os.getenv("DB_USER", "root")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DB_NAME: str = os.getenv("DB_NAME", "adt_system")

    @property
    def DATABASE_URL(self) -> str:
        custom_url = os.getenv("DATABASE_URL")
        if custom_url:
            return custom_url
        # MySQL URL format: mysql+pymysql://user:password@host:port/dbname
        if self.DB_PASSWORD:
            return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"
        return f"mysql+pymysql://{self.DB_USER}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"

    @property
    def SERVER_URL(self) -> str:
        # Connection string to MySQL server without database name (for auto-creating DB)
        if self.DB_PASSWORD:
            return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/?charset=utf8mb4"
        return f"mysql+pymysql://{self.DB_USER}@{self.DB_HOST}:{self.DB_PORT}/?charset=utf8mb4"

    # Mistral AI
    MISTRAL_API_KEY: str = os.getenv("MISTRAL_API_KEY", "")
    MISTRAL_BASE_URL: str = os.getenv("MISTRAL_BASE_URL", "https://api.mistral.ai/v1")
    MISTRAL_MODEL: str = os.getenv("MISTRAL_MODEL", "open-mistral-nemo")

    # Telegram Bot
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    AUTHORIZED_USER_ID: int = int(os.getenv("AUTHORIZED_USER_ID", "0"))
    RUN_TELEGRAM_BOT: bool = os.getenv("RUN_TELEGRAM_BOT", "false").lower() in ("true", "1", "yes")

    # Default Profit Sharing (%)
    DEFAULT_KARYAWAN_1_PERCENT: float = float(os.getenv("DEFAULT_KARYAWAN_1_PERCENT", "25"))
    DEFAULT_KARYAWAN_2_PERCENT: float = float(os.getenv("DEFAULT_KARYAWAN_2_PERCENT", "25"))
    DEFAULT_KAS_PERUSAHAAN_PERCENT: float = float(os.getenv("DEFAULT_KAS_PERUSAHAAN_PERCENT", "50"))

settings = Settings()
os.makedirs(settings.PDF_OUTPUT_DIR, exist_ok=True)

os.makedirs(settings.PO_UPLOAD_DIR, exist_ok=True)
