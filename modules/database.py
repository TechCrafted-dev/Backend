import time

from modules.config import log_database

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
    source_id = Column(String, nullable=False)                   # ID de la Fuente
    title = Column(String, nullable=False, unique=True)          # Título de la noticia
    introduction = Column(String, nullable=False)                # Introducción a la noticia
    content = Column(String, nullable=False)                     # Contenido de la noticia
    published_at = Column(DateTime, nullable=False)              # Fecha de publicación
    url = Column(String, nullable=False, unique=True)            # URL de la noticia

class NewsSource(Base):
    __tablename__ = 'news_source'
    id = Column(Integer, primary_key=True, autoincrement=True)   # ID de la fuente
    name = Column(String, nullable=False, unique=True)           # Nome de la fuente
    url = Column(String, nullable=False, unique=True)            # URL de la fuente
    rss = Column(String, nullable=False, unique=True)            # URL del RSS de la fuente
    added_at = Column(DateTime, nullable=False)                  # Fecha de adición de la fuente
    score = Column(Integer, nullable=False, default=0)           # Puntuación de la fuente

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


def check_table_structure(model, inspector, logger):
    """
    Compara la estructura de un modelo SQLAlchemy con la tabla real en la BD.
    Si no coincide, la tabla se elimina para ser recreada, perdiendo todos los datos.
    """
    table_name = model.__tablename__
    if not inspector.has_table(table_name):
        logger.info(f"La tabla '{table_name}' no existe y será creada.")
        return  # No hay nada que comparar, create_all se encargará

    db_columns = {col['name'] for col in inspector.get_columns(table_name)}
    model_columns = {col.name for col in model.__table__.columns}

    missing_in_db = model_columns - db_columns
    extra_in_db = db_columns - model_columns

    if not missing_in_db and not extra_in_db:
        logger.info(f"La estructura de la tabla '{table_name}' coincide con el modelo.")

    else:
        logger.warning(f"La estructura de la tabla '{table_name}' no coincide con el modelo.")
        if missing_in_db:
            logger.warning(f"Columnas del modelo FALTANTES en la BD: {missing_in_db}")

        if extra_in_db:
            logger.warning(f"Columnas EXTRA en la BD no definidas en el modelo: {extra_in_db}")

        logger.warning(f"ATENCIÓN: Se eliminará y recreará la tabla '{table_name}'. ¡TODOS LOS DATOS EN ESTA TABLA SE PERDERÁN!")
        try:
            model.__table__.drop(bind=engine)
            logger.info(f"Tabla '{table_name}' eliminada. Será recreada con el nuevo esquema.")

        except Exception as e:
            logger.error(f"No se pudo eliminar la tabla '{table_name}': {e}. La aplicación puede ser inestable.")


def init_db():
    inspector = inspect(engine)

    log_database.info("Verificando la estructura de las tablas de la base de datos...")
    # Itera sobre todos los modelos registrados en Base para verificar su estructura
    for mapper in Base.registry.mappers:
        model_class = mapper.class_
        check_table_structure(model_class, inspector, log_database)

    # Base.metadata.create_all se asegura de que las tablas que no existen sean creadas.
    Base.metadata.create_all(bind=engine)
    log_database.info("Inicialización de la base de datos completada.")

# Inicializar la base de datos al cargar el módulo
init_db()


""" REPOSITORIOS """
def set_repo(new_repo: Repos):
    with SessionLocal() as session:
        session.add(new_repo)
        session.commit()
        log_database.info(f"Repositorio {new_repo.name} guardado exitosamente.")

def get_repos(order_by: str = "id", desc: bool = True):
    with SessionLocal() as session:
        column = getattr(Repos, order_by)

        order_clause = column.desc() if desc else column.asc()
        repos = session.query(Repos).order_by(order_clause).all()

        if repos:
            log_database.info(f"{len(repos)} repositorios recuperados exitosamente.")
            return repos

        else:
            log_database.warning("No se encontraron repositorios.")
            return []

def get_repo(by_id: int):
    with SessionLocal() as session:
        repo = session.query(Repos).filter(Repos.id == by_id).first()
        if repo:
            log_database.info(f"Repositorio {repo.name} recuperado exitosamente.")
            return repo

        else:
            log_database.warning(f"Repositorio con ID {by_id} no encontrado.")
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

def delete_repo(repo_id: int):
    with SessionLocal() as session:
        repo = session.query(Repos).filter(Repos.id == repo_id).first()
        if repo:
            session.delete(repo)
            session.commit()
            log_database.info(f"Repositorio {repo.name} eliminado exitosamente.")

        else:
            log_database.warning(f"Repositorio con ID {repo_id} no encontrado para eliminar.")


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

def get_posts(order_by: str = "id", desc: bool = True):
    with SessionLocal() as session:
        column = getattr(Posts, order_by)

        order_clause = column.desc() if desc else column.asc()
        posts = session.query(Posts).order_by(order_clause).all()

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
        log_database.info(f"Noticia [{new_news.title}] guardada exitosamente.")

def get_news():
    with SessionLocal() as session:
        news = session.query(News).all()
        if news:
            log_database.info(f"{len(news)} noticias recuperadas exitosamente.")
            return news

        else:
            log_database.warning("No se encontraron noticias.")
            return []

def get_news_by_url(url: str):
    with SessionLocal() as session:
        news = session.query(News).filter(News.url == url).first()
        if news:
            log_database.info(f"Noticia [{news.title}] recuperada exitosamente.")
            return news

        else:
            log_database.warning(f"Noticia con URL [{url}] no encontrada.")
            return None


""" FUENTES DE NOTICIAS """
def save_news_source(new_source: NewsSource):
    with SessionLocal() as session:
        session.add(new_source)
        session.commit()
        log_database.info(f"Fuente de noticias guardada exitosamente.")

def get_news_sources():
    with SessionLocal() as session:
        sources = session.query(NewsSource).all()
        if sources:
            log_database.info(f"{len(sources)} fuentes de noticias recuperadas exitosamente.")
            return sources

        else:
            log_database.warning("No se encontraron fuentes de noticias.")
            return []

def get_source_id_by_name(name: str):
    with SessionLocal() as session:
        source = session.query(NewsSource).filter(NewsSource.name == name).first()
        if source:
            log_database.info(f"ID de la fuente de noticias [{name}] recuperado exitosamente.")
            return source.id

        else:
            log_database.warning(f"Fuente de noticias con URL [{name}] no encontrada.")
            return None
