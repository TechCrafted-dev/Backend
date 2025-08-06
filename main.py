import re
import uvicorn
import requests

from pytz import timezone
from typing import Optional
from dateutil.parser import isoparse
from requests.auth import HTTPBasicAuth
from contextlib import asynccontextmanager

from modules import database, github, techAI             # Módulos de la aplicación
from modules.config import settings                      # Configuración de la aplicación
from modules.config import tags_metadata, Tags           # Rutas Tags del Swagger
from modules.config import LOGGING_CONFIG, log_main      # Configuración de logging
from modules.config import OrderField, OrderDirection    # Ordenación de los repositorios

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, JSONResponse


# ------ Schedule Setup ------
@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = AsyncIOScheduler(timezone=timezone("Europe/Madrid"))

    scheduler.add_job(
        search_news,
        'cron',
        day_of_week='sun',
        hour=0,
        minute=0,
        id='search_news_job',
        replace_existing=True,
        misfire_grace_time=600)

    scheduler.add_job(
        update_repos,
        'cron',
        hour=23,
        minute=0,
        id='update_repos_job',
    )

    scheduler.add_job(
        update_all_posts,
        'cron',
        day_of_week='wed',
        hour=0,
        minute=30,
        id='update_all_posts_job',
        replace_existing=True,
        misfire_grace_time=600
    )

    scheduler.start()
    try:
        yield
    finally:
        scheduler.shutdown(wait=False)


# ------ FastAPI Setup ------
app = FastAPI(
    title="TechCrafted API",
    description="API for TechCrafted, a platform for tech enthusiasts.",
    version="1.0.0",
    openapi_tags=tags_metadata,
    lifespan=lifespan
)

# ------ FastAPI CORS ------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ajusta a tu dominio en producción
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------ Gitea config ------
GITEA_DATA   = settings['GITEA']
GITEA_URL    = GITEA_DATA['url']
GITEA_USER   = GITEA_DATA['user']
GITEA_TOKEN  = GITEA_DATA['token']
GITEA_BLOG   = GITEA_DATA['blog']
GITEA_NEWS   = GITEA_DATA['news']


# ------ UTILS ------
async def generate_post_logic(data: dict, pipeline) -> database.Posts | None:
    try:
        log_main.info(f"Generando post para repositorio {data['name']}...")

        response = await techAI.gen_post(data, mode=pipeline)
        if response is None:
            return response

        markdown_pattern = re.compile(r'```markdown\n(.*?)```', re.DOTALL)
        post = ''.join(markdown_pattern.findall(response)) or response

        new_post = database.Posts(
            id=data["id"],
            title=data["name"],
            description=data["description"],
            created_at=isoparse(data["created_at"]),
            updated_at=isoparse(data["updated_at"]),
            article=post
        )

        return new_post

    except Exception as e:
        log_main.error(f"Error generating post for repository {data['name']}: {e}")
        raise e


# ------ ENDPOINTS ------
@app.get("/health", tags=[Tags.state],
         response_class=PlainTextResponse,
         summary="Health check endpoint",
         description="Returns 'ok' if the service is running.")
async def health():
    return "ok"


# ------ GITHUB USER ENDPOINTS ------
@app.get("/github-user", tags=[Tags.github], summary="Get GitHub user data",
         description="Fetches and returns the GitHub user data.")
async def get_github_user():
    try:
        log_main.info("Fetching GitHub user data...")
        user = github.get_user_info()

        if not user:
            log_main.warning("GitHub user not found.")
            return {"error": "GitHub user not found"}

        return user

    except Exception as e:
        log_main.error(f"Error fetching GitHub user data: {e}")
        return {"error": str(e)}


@app.get("/github-user/data", tags=[Tags.github], summary="Get GitHub data",
         description="Fetches and returns the latest GitHub repository data.")
async def get_github_data():
    try:
        log_main.info("Fetching GitHub repository data...")
        repos = github.get_repos_data()

        if not repos:
            log_main.warning("No repositories found.")
            return {"error": "No repositories found"}

        return repos

    except Exception as e:
        log_main.error(f"Error fetching GitHub data: {e}")
        return {"error": str(e)}


# ------ GITHUB ORGANIZATION ENDPOINTS ------
@app.get("/github-orgs", tags=[Tags.github_orgs], summary="Get GitHub user organizations",
         description="Fetches and returns the GitHub user organizations.")
async def get_github_user_orgs():
    try:
        log_main.info("Fetching GitHub user organizations...")
        orgs = github.get_user_orgs()

        if not orgs:
            log_main.warning("GitHub user organizations not found.")
            return {"error": "GitHub user organizations not found"}

        return orgs

    except Exception as e:
        log_main.error(f"Error fetching GitHub user organizations: {e}")
        return {"error": str(e)}


@app.get("/github-orgs/data", tags=[Tags.github_orgs], summary="Get GitHub organizations data",
         description="Fetches and returns the latest GitHub organizations data.")
async def get_github_orgs_data():
    try:
        log_main.info(f"Fetching GitHub organization data")
        org_data = github.get_orgs_data()

        if not org_data:
            log_main.warning(f"No data found for organization.")
            return {"error": f"No data found for organization"}

        return org_data

    except Exception as e:
        log_main.error(f"Error fetching GitHub organization data: {e}")
        return {"error": str(e)}


# ------ REPOSITORIES ENDPOINTS ------
@app.get("/repos", tags=[Tags.repos], summary="Get all database repositories",
         description="Returns a list of all repositories stored in the database.",)
async def get_repos(
    order_by: Optional[OrderField] = Query(
        default=None,
        description="Campo por el que ordenar"
    ),
    direction: OrderDirection = Query(
        default=OrderDirection.asc,
        description="Dirección de ordenación (asc o desc)"
    ),
):
    try:
        if order_by is None:
            return database.get_repos()

        return database.get_repos(
            order_by=order_by.value,
            desc=(direction == OrderDirection.desc)
        )

    except Exception as e:
        log_main.error(f"Error fetching repositories: {e}")
        # Mejor devolver un 500 real
        raise HTTPException(status_code=500, detail="Error fetching repositories")


@app.get("/repos/{repo_id}", tags=[Tags.repos], summary="Get repository by database ID",
         description="Returns a repository specific by its ID if it exists in the database.")
async def get_repo(repo_id: int):
    try:
        repo = database.get_repo(repo_id)
        if repo:
            return repo

        else:
            return {"error": "Repository not found"}

    except Exception as e:
        log_main.error(f"Error fetching repository {repo_id}: {e}")
        return {"error": str(e)}


@app.post("/repos", tags=[Tags.repos], summary="Update all database repositories ",
          description="Gets GitHub repositories and updates the database.")
async def update_repos():
    new_data = github.get_repos_data()
    old_data = database.get_repos()

    for data in new_data:
        log_main.info(f"Actualizando repositorio {data['name']}...")

        existing_repo = database.get_repo(data["id"])

        updated_repo = database.Repos(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            url=data["url"],
            language=data["language"],
            stars=data["stars"],
            forks=data["forks"],
            watchers=data["watchers"],
            views=data["views"],
            unique_views=data["unique_views"],
            clones=data["clones"],
            unique_clones=data["unique_clones"],
            created_at=isoparse(data["created_at"]),
            updated_at=isoparse(data["updated_at"]),
        )

        if existing_repo is not None:
            database.update_repo(updated_repo)

        else:
            log_main.info(f"Detectado nuevo repositorio {data['name']}, guardando...")
            database.set_repo(updated_repo)

    for old_repo in old_data:
        if not any(new_repo["id"] == old_repo.id for new_repo in new_data):
            log_main.info(f"Repositorio {old_repo.name} no encontrado en los datos nuevos, eliminando...")
            database.delete_repo(old_repo.id)

    return {"message": "Repositories updated successfully"}


@app.delete("/repos/{repo_id}", tags=[Tags.repos], summary="Delete repository by database ID",
            description="Delete a specific repository by its ID if it exists.")
async def delete_repo(repo_id: int):
    try:
        log_main.info(f"Eliminando repositorio {repo_id}...")

        repo = database.get_repo(repo_id)
        if repo:
            database.delete_repo(repo_id)
            return {"message": f"Repository {repo_id} deleted successfully"}

        else:
            log_main.warning(f"Repository {repo_id} not found.")
            return {"error": "Repository not found"}

    except Exception as e:
        log_main.error(f"Error deleting repository {repo_id}: {e}")
        return {"error": str(e)}


# ------ POSTS ENDPOINTS ------
@app.get("/posts", tags=[Tags.post], summary="Get all posts",
         description="Returns a list of all posts stored in the database.")
async def get_repos(
    order_by: Optional[OrderField] = Query(
        default=None,
        description="Campo por el que ordenar"
    ),
    direction: OrderDirection = Query(
        default=OrderDirection.asc,
        description="Dirección de ordenación (asc o desc)"
    ),
):
    try:
        if order_by is None:
            return database.get_posts()

        return database.get_posts(
            order_by=order_by.value,
            desc=(direction == OrderDirection.desc)
        )

    except Exception as e:
        log_main.error(f"Error fetching repositories: {e}")
        # Mejor devolver un 500 real
        raise HTTPException(status_code=500, detail="Error fetching repositories")


@app.get("/posts/{repo_id}", tags=[Tags.post], summary="Get post by repository ID",
         description="Returns a specific post by its repository ID if it exists.")
async def get_post(repo_id: int):
    log_main.info(f"Obteniendo post para repositorio {repo_id}...")
    try:

        post = database.get_post(repo_id)
        if post:
            return {
                "id": post.id,
                "title": post.title,
                "description": post.description,
                "created_at": post.created_at,
                "updated_at": post.updated_at,
                "article": post.article
            }

        else:
            log_main.warning(f"Post para repositorio {repo_id} no encontrado.")
            return {"error": "Post not found"}

    except Exception as e:
        log_main.error(f"Error fetching post for repository {repo_id}: {e}")
        return {"error": str(e)}


@app.put("/posts/update_all", tags=[Tags.post], summary="Update all post",
         description="Updates all existing posts in the database based on the latest repository data.")
async def update_all_posts():
    log_main.info(f"Actualizando todos los posts...")

    try:
        repos = database.get_repos()
        if not repos:
            log_main.warning("No hay repositorios para actualizar posts.")
            return {"error": "No repositories found"}


        update = False
        count = 1
        for repo in repos:
            log_main.info(f"{count}/{len(repos)} Repositorio {repo.id} - {repo.name}")
            repo_json = {
                "id": repo.id,
                "name": repo.name,
                "description": repo.description,
                "url": repo.url,
                "language": repo.language,
                "stars": repo.stars,
                "forks": repo.forks,
                "watchers": repo.watchers,
                "views": repo.views,
                "unique_views": repo.unique_views,
                "clones": repo.clones,
                "unique_clones": repo.unique_clones,
                "created_at": repo.created_at.isoformat(),
                "updated_at": repo.updated_at.isoformat(),
            }

            pipeline = techAI.Pipeline.EVAL
            post = await generate_post_logic(repo_json, pipeline)

            if post is not None:
                database.update_post(post)
                update = True

            count += 1

        if update:
            log_main.info("Se han realizado cambios en la base de datos")
            log_main.info("Reconstruyendo BlogPage...")

            url = f"{GITEA_URL}/job/{GITEA_BLOG}/job/main/build"
            response = requests.post(url, auth=HTTPBasicAuth(GITEA_USER, GITEA_TOKEN))

            if response.status_code == 201:
                log_main.info("BlogPage reconstruido correctamente.")

            else:
                log_main.error(f"Error al reconstruir BlogPage: {response.status_code} - {response.text}")

        return {"message": "All posts updated successfully"}

    except Exception as e:
        log_main.error(f"Error updating all posts: {e}")
        return {"error": str(e)}


@app.put("/posts/{repo_id}", tags=[Tags.post], summary="Update post",
         description="Updates an existing post for a specific repository by its ID if it exists.")
async def update_post(repo_id: int):
    try:
        log_main.info(f"Actualizando post para repositorio {repo_id}...")

        repo = database.get_repo(repo_id)
        repo_json = {
            "id": repo.id,
            "name": repo.name,
            "description": repo.description,
            "url": repo.url,
            "language": repo.language,
            "stars": repo.stars,
            "forks": repo.forks,
            "watchers": repo.watchers,
            "views": repo.views,
            "unique_views": repo.unique_views,
            "clones": repo.clones,
            "unique_clones": repo.unique_clones,
            "created_at": repo.created_at.isoformat(),
            "updated_at": repo.updated_at.isoformat(),
        }

        if repo:
            pipeline = techAI.Pipeline.POST
            post = await generate_post_logic(repo_json, pipeline)
            database.update_post(post)

            return {"message": "Post updated successfully"}

        else:
            return {"error": "Post not found"}

    except Exception as e:
        log_main.error(f"Error updating post for repository {repo_id}: {e}")
        return {"error": str(e)}


@app.post("/posts/{repo_id}", tags=[Tags.post], response_class=JSONResponse,summary="Generate and save a new post",
         description="Generates a new post based on the provided repository data and saves it to the database if it does not already exist.")
async def gen_post(repo_id: int):
    try:
        repo = database.get_repo(repo_id)
        repo_json = {
            "id": repo.id,
            "name": repo.name,
            "description": repo.description,
            "url": repo.url,
            "language": repo.language,
            "stars": repo.stars,
            "forks": repo.forks,
            "watchers": repo.watchers,
            "views": repo.views,
            "unique_views": repo.unique_views,
            "clones": repo.clones,
            "unique_clones": repo.unique_clones,
            "created_at": repo.created_at.isoformat(),
            "updated_at": repo.updated_at.isoformat(),
        }

        pipeline = techAI.Pipeline.POST
        new_post = await generate_post_logic(repo_json, pipeline)

        if database.get_post(repo_id) is None:
            database.save_post(new_post)

        return {"message": "Post create successfully"}

    except Exception as e:
        log_main.error(f"Error generating post: {e}")
        return {"error": str(e)}


# ------ NEWS ENDPOINTS ------
@app.get("/news", tags=[Tags.news], summary="Get all news",
         description="Returns a list of all news articles stored in the database.")
async def get_news():
    log_main.info("Obteniendo todas las noticias...")
    try:
        news = database.get_news()
        if news:
            return [
                {
                    "title": item.title,
                    "summary": item.summary,
                    "created_at": item.created_at,
                    "language": item.language,
                    "source": item.source,
                    "url": item.url
                } for item in news
            ]

        else:
            return {"error": "No news found"}

    except Exception as e:
        log_main.error(f"Error fetching news: {e}")
        return {"error": str(e)}


@app.post("/search_news", tags=[Tags.news], summary="Get latest news",
         description="Fetches the latest news from the techAI service.")
async def search_news():
    log_main.info("Obteniendo últimas noticias...")

    try:
        news = await techAI.get_news(mode=techAI.Pipeline.NEWS)
        if not news:
            log_main.warning("No se encontraron noticias.")
            return {"error": "No news found"}

        for item in news:
            save_news = database.News(
                title=item["title"],
                summary=item["summary"],
                created_at=isoparse(item["date"]),
                language=item["language"],
                source=item["source"],
                url=item["url"],
            )

            database.save_news(save_news)

        return {"news": news}

    except Exception as e:
        log_main.error(f"Error fetching news: {e}")
        return {"error": str(e)}


if __name__ == "__main__":
    uvicorn.run("main:app",
                host="0.0.0.0",
                port=3000,
                reload=True,
                log_config=LOGGING_CONFIG)