import os
import time

from config import log_database

from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy import create_engine, inspect, event, Engine


Base = declarative_base()

class Repos(Base):
    __tablename__ = 'repos'
    id = Column(Integer, primary_key=True, autoincrement=False)  # ID del repositorio
    name = Column(String, nullable=False, unique=True)           # Nombre del repositorio
    description = Column(String, nullable=True)                  # Descripción del repositorio
    url = Column(String, nullable=False)                         # URL del repositorio
    language = Column(String, nullable=True)                     # Lenguaje de programación del repositorio
    stars = Column(Integer, nullable=False, default=0)           # Número de estrellas del repositorio
    forks = Column(Integer, nullable=False, default=0)           # Número de forks del repositorio
    watchers = Column(Integer, nullable=False, default=0)        # Número de watchers del repositorio
    views = Column(Integer, nullable=False, default=0)           # Número de vistas del repositorio
    unique_views = Column(Integer, nullable=False, default=0)    # Número de vistas únicas del repositorio
    clones = Column(Integer, nullable=False, default=0)          # Número de clones del repositorio
    unique_clones = Column(Integer, nullable=False, default=0)   # Número de clones únicos del repositorio
    created_at = Column(DateTime, nullable=False)                # Fecha de creación del repositorio
    updated_at = Column(DateTime, nullable=False)                # Fecha de última actualización del repositorio

class Posts(Base):
    __tablename__ = 'posts'
    id = Column(Integer, primary_key=True, autoincrement=False)  # ID del repositorio y post
    title = Column(String, nullable=False, unique=True)          # Título del post
    description = Column(String, nullable=False)                 # Descripción del post
    created_at = Column(DateTime, nullable=False)                # Fecha de creación del post
    updated_at = Column(DateTime, nullable=False)                # Fecha de última actualización del post
    article = Column(String, nullable=False)                     # Contenido del post

class News(Base):
    __tablename__ = 'news'
    id = Column(Integer, primary_key=True, autoincrement=True)   # ID de la noticia
    title = Column(String, nullable=False, unique=True)          # Título de la noticia
    summary = Column(String, nullable=False)                     # Contenido de la noticia
    created_at = Column(DateTime, nullable=False)                # Fecha de la noticia
    language = Column(String, nullable=False)                    # Lenguaje de programación
    source = Column(String, nullable=False)                      # Fuente de la noticia
    url = Column(String, nullable=False)                         # URL de la noticia


# Configuración de la base de datos SQLite
DATABASE_URL = "sqlite:///data/repositories.db"
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Registra las consultas SQL
@event.listens_for(Engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    conn.info.setdefault('query_start_time', []).append(time.time())
    log_database.debug(f"Ejecutando SQL: {statement} | Parámetros: {parameters}")


@event.listens_for(Engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    total = time.time() - conn.info['query_start_time'].pop()
    log_database.debug(f"Consulta completada en {total:.3f}s.")


# Crear la base de datos solo si no existe
# Obtener la ruta real del archivo de base de datos a partir de DATABASE_URL
db_path = DATABASE_URL.replace("sqlite:///", "")
if not os.path.exists(db_path):
    Base.metadata.create_all(bind=engine)

inspector = inspect(engine)

if not inspector.has_table("repos"):
    Base.metadata.tables['repos'].create(engine)
    log_database.info("Tabla 'repos' creada exitosamente.")

if not inspector.has_table("posts"):
    Base.metadata.tables['posts'].create(engine)
    log_database.info("Tabla 'posts' creada exitosamente.")


""" REPOSITORIOS """
def set_repo(new_repo: Repos):
    with SessionLocal() as session:
        session.add(new_repo)
        session.commit()
        log_database.info(f"Repositorio {new_repo.name} guardado exitosamente.")


def get_repos():
    with SessionLocal() as session:
        repos = session.query(Repos).all()
        if repos:
            log_database.info(f"{len(repos)} repositorios recuperados exitosamente.")
            return repos
        else:
            log_database.warning("No se encontraron repositorios.")
            return []


def get_repo(id: int):
    with SessionLocal() as session:
        repo = session.query(Repos).filter(Repos.id == id).first()
        if repo:
            log_database.info(f"Repositorio {repo.name} recuperado exitosamente.")
            return repo

        else:
            log_database.warning(f"Repositorio con ID {id} no encontrado.")
            return None


def update_repo(updated_repo):
    with SessionLocal() as session:
        existing_repo = session.query(Repos).filter(Repos.id == updated_repo.id).first()

        if existing_repo:
            existing_repo.name = updated_repo.name
            existing_repo.description = updated_repo.description
            existing_repo.url = updated_repo.url
            existing_repo.language = updated_repo.language
            existing_repo.stars = updated_repo.stars
            existing_repo.forks = updated_repo.forks
            existing_repo.watchers = updated_repo.watchers
            existing_repo.views = updated_repo.views
            existing_repo.unique_views = updated_repo.unique_views
            existing_repo.clones = updated_repo.clones
            existing_repo.unique_clones = updated_repo.unique_clones
            existing_repo.updated_at = updated_repo.updated_at

            session.commit()

            log_database.info(f"Repositorio {updated_repo.name} actualizado exitosamente.")

        else:
            log_database.warning(f"Repositorio con ID {updated_repo.id} no encontrado para actualizar.")


""" POSTS"""
def save_post(new_post: Posts):
    with SessionLocal() as session:
        session.add(new_post)
        session.commit()
        log_database.info(f"Post {new_post.title} guardado exitosamente.")


def get_post(repo_id):
    with SessionLocal() as session:
        post = session.query(Posts).filter(Posts.id == repo_id).first()
        if post:
            log_database.info(f"Post {post.title} recuperado exitosamente.")
            return post

        else:
            log_database.warning(f"Post con ID {repo_id} no encontrado.")
            return None


def update_post(post):
    with SessionLocal() as session:
        existing_post = session.query(Posts).filter(Posts.id == post.id).first()
        if existing_post:
            existing_post.title = post.title
            existing_post.description = post.description
            existing_post.article = post.article
            existing_post.updated_at = post.updated_at
            session.commit()
            log_database.info(f"Post {post.title} actualizado exitosamente.")

        else:
            log_database.warning(f"Post con ID {post.id} no encontrado para actualizar.")


def get_posts():
    with SessionLocal() as session:
        posts = session.query(Posts).all()
        if posts:
            log_database.info(f"{len(posts)} posts recuperados exitosamente.")
            return posts
        else:
            log_database.warning("No se encontraron posts.")
            return []


""" NOTICIAS """
def save_news(new_news: News):
    with SessionLocal() as session:
        session.add(new_news)
        session.commit()
        log_database.info(f"Noticia {new_news.title} guardada exitosamente.")