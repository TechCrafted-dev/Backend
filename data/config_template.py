import logging
import logging.config


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


# Configuración de GitHub
GITHUB_USERNAME = ""
GITHUB_TOKEN = ""

# Configuración de OpenAI
OPENAI_API_KEY = ""
