import re
import github
import techAI
import uvicorn
import database

from dateutil.parser import isoparse
from config import LOGGING_CONFIG, log_main

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI()

# CORS para permitir peticiones desde el frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ajusta a tu dominio en producción
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def generate_post_logic(data: dict) -> database.Posts:
    try:
        log_main.info(f"Generando post para repositorio {data['name']}...")

        mode = techAI.Pipeline.POST
        response = await techAI.gen_post(data, mode=mode)
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


@app.post("/posts/{repo_id}", response_class=JSONResponse,summary="Generate and save a new post",
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

        new_post = await generate_post_logic(repo_json)

        if database.get_post(repo_id) is None:
            database.save_post(new_post)

        return {"message": "Post updated successfully"}

    except Exception as e:
        log_main.error(f"Error generating post: {e}")
        return {"error": str(e)}


@app.put("/posts/{repo_id}", summary="Update post",
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
            post = await generate_post_logic(repo_json)
            database.update_post(post)

            return {"message": "Post updated successfully"}

        else:
            return {"error": "Post not found"}

    except Exception as e:
        log_main.error(f"Error updating post for repository {repo_id}: {e}")
        return {"error": str(e)}


@app.put("/posts/update_all", summary="Update all post",
         description="Updates all existing posts in the database based on the latest repository data.")
async def update_all_posts():
    try:
        repos = database.get_repos()
        if not repos:
            log_main.warning("No hay repositorios para actualizar posts.")
            return {"error": "No repositories found"}

        log_main.info(f"Actualizando {len(repos)} posts...")

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

            post = await generate_post_logic(repo_json)
            database.update_post(post)
            count += 1

        return {"message": "All posts updated successfully"}

    except Exception as e:
        log_main.error(f"Error updating posts: {e}")
        return {"error": str(e)}


@app.get("/posts/{repo_id}", summary="Get post by repository ID",
         description="Returns a specific post by its repository ID if it exists.")
async def get_post(repo_id: int):
    try:
        log_main.info(f"Obteniendo post para repositorio {repo_id}...")

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


@app.get("/posts", summary="Get all posts",
         description="Returns a list of all posts stored in the database.")
async def get_posts():
    try:
        log_main.info("Obteniendo todos los posts...")

        posts = database.get_posts()
        if posts:
            return [
                {
                    "id": post.id,
                    "title": post.title,
                    "description": post.description,
                    "created_at": post.created_at,
                    "updated_at": post.updated_at,
                    "article": post.article
                } for post in posts
            ]

        else:
            return {"error": "No posts found"}

    except Exception as e:
        log_main.error(f"Error fetching posts: {e}")
        return {"error": str(e)}


@app.post("/repos/update", summary="Update repositories",
          description="Fetches repositories from GitHub and updates them in the database if they exist.")
async def update_repos():
    try:
        repos = github.get_repos_data()

        for repo in repos:
            log_main.info(f"Actualizando repositorio {repo['name']}...")

            existing_repo = database.get_repo(repo["id"])

            updated_repo = database.Repos(
                id=repo["id"],
                name=repo["name"],
                description=repo["description"],
                url=repo["url"],
                language=repo["language"],
                stars=repo["stars"],
                forks=repo["forks"],
                watchers=repo["watchers"],
                views=repo["views"],
                unique_views=repo["unique_views"],
                clones=repo["clones"],
                unique_clones=repo["unique_clones"],
                created_at=isoparse(repo["created_at"]),
                updated_at=isoparse(repo["updated_at"]),
            )

            if existing_repo is not None:
                database.update_repo(updated_repo)

            else:
                log_main.info(f"Detectado nuevo repositorio {repo['name']}, guardando...")
                database.set_repo(updated_repo)

        return {"message": "Repositories updated successfully"}

    except Exception as e:
        log_main.error(f"Error updating repositories: {e}")
        return {"error": str(e)}


@app.post("/repos", summary="Set repositories",
          description="Fetches repositories from GitHub and saves them to the database if they do not exist.")
async def set_repos():
    try:
        repos = github.get_repos_data()

        for repo in repos:
            log_main.info(f"Guardando repositorio {repo['name']}...")

            if database.get_repo(repo["id"]) is None:
                new_repo = database.Repos(
                    id=repo["id"],
                    name=repo["name"],
                    description=repo["description"],
                    url=repo["url"],
                    language=repo["language"],
                    stars=repo["stars"],
                    forks=repo["forks"],
                    watchers=repo["watchers"],
                    views=repo["views"],
                    unique_views=repo["unique_views"],
                    clones=repo["clones"],
                    unique_clones=repo["unique_clones"],
                    created_at=isoparse(repo["created_at"]),
                    updated_at=isoparse(repo["updated_at"]),
                )

                database.set_repo(new_repo)

        log_main.info("All repositories saved successfully.")
        return {"message": "Repositories saved successfully"}

    except Exception as e:
        log_main.error(f"Error saving repositories: {e}")
        return {"error": str(e)}


@app.get("/repos/{repo_id}", summary="Get repository by ID",
         description="Returns a specific repository by its ID if it exists.")
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


@app.get("/repos", summary="Get all repositories",
         description="Returns a list of all repositories stored in the database.")
async def get_repos():
    try:
        repos = database.get_repos()
        return repos

    except Exception as e:
        log_main.error(f"Error fetching repositories: {e}")
        return {"error": str(e)}


@app.get("/github-data", summary="Get GitHub data",
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


@app.get("/health", response_class=PlainTextResponse,
         summary="Health check endpoint",
         description="Returns 'ok' if the service is running.")
async def health():
    return "ok"


if __name__ == "__main__":
    uvicorn.run("main:app",
                host="0.0.0.0",
                port=3000,
                reload=True,
                log_config=LOGGING_CONFIG)