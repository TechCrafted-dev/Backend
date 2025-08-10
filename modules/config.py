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

# Configuración centralizada de logging
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
            "level": "WARNING",
            "propagate": False,
        },
        "main": {                       # Logger principal de tu aplicación
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "database": {                   # Logger para operaciones de base de datos
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "github": {                     # Logger para operaciones relacionadas con GitHub
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "techAI": {                     # Logger para elementos relacionados con techAI
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

# Aplicar la configuración global de logging
logging.config.dictConfig(LOGGING_CONFIG)

# Crear loggers para los módulos específicos
log_main = logging.getLogger("main")
log_database = logging.getLogger("database")
log_github = logging.getLogger("github")
log_techAI = logging.getLogger("techAI")

settings = load_config()