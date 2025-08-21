import json
import logging.config

from enum import Enum
from pathlib import Path
from typing import Any, Dict, List


class Tags(str, Enum):
    state = "States"
    github = "GitHub"
    github_orgs = "GitHub Orgs"
    repos = "Repositories"
    post = "Post"
    news = "News"


class OrderField(str, Enum):
    id = "id"
    name = "name"
    created_at = "created_at"
    updated_at = "updated_at"


class OrderDirection(str, Enum):
    asc = "asc"
    desc = "desc"


def load_config() -> dict:
    try:
        with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)

    except FileNotFoundError:
        raise RuntimeError(
            f"El archivo de configuración no encontrado"
        )


TAG_DESCRIPTIONS: Dict[str, str] = {
    Tags.state.value:       "API health and resources.",
    Tags.github.value:      "Operations on the GitHub user.",
    Tags.github_orgs.value: "Consultation of user organizations on GitHub.",
    Tags.repos.value:       "Repository CRUD.",
    Tags.post.value:        "Posts generated from repositories.",
    Tags.news.value:        "Search and publication of news.",
}


tags_metadata: List[Dict[str, Any]] = [
    {
        "name": tag.value,
        "description": TAG_DESCRIPTIONS.get(tag.value),
    }
    for tag in Tags
]


CONFIG_FILE_PATH = Path(__file__).parent / ".." / "data" / "config.json"

settings = load_config()

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s [ %(levelname)s ] [ %(lineno)d ] %(name)s - %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
        },
    },
    "loggers": {
        "uvicorn": {                    # Logger para Uvicorn
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "uvicorn.error": {              # Logger para errores de Uvicorn
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "uvicorn.access": {             # Logger para accesos de Uvicorn
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "httpx": {                      # Logger para httpx
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "config": {                     # Logger para el configurador
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "main": {                       # Logger para el main principal
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "database": {                   # Logger de la base de datos
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "github": {                     # Logger de la API de GitHub
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "techAI": {                     # Logger de la herramienta del LLM
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "": {                           # Logger raíz
            "handlers": ["console"],
            "level": "INFO",
        },
    },
}

# Modifica LOGGING_CONFIG con los ajustes del usuario
if settings.get('LOGGER'):
    for key, value in settings['LOGGER'].items():
        if key in LOGGING_CONFIG['loggers']:
            LOGGING_CONFIG['loggers'][key]['level'] = value

logging.config.dictConfig(LOGGING_CONFIG)

log_config = logging.getLogger("config")      # Logger del configurador
log_main = logging.getLogger("main")          # Logger para el main principal
log_database = logging.getLogger("database")  # Logger de la base de datos
log_github = logging.getLogger("github")      # Logger de la API de GitHub
log_techAI = logging.getLogger("techAI")      # Logger de la herramienta del LLM

if settings.get('LOGGER'):
    log_config.info("Logging personalizado activado.")
    for key, value in settings['LOGGER'].items():
        if key in LOGGING_CONFIG['loggers']:
            log_config.info(f"Nivel de '{key}' establecido a: {value}")
