import json
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
    log_main.info(f"Generando post para repositorio {data['name']}...")

    response = techAI.gen_post(data)
    markdown_pattern = re.compile(r'```markdown\n(.*?)```', re.DOTALL)
    post = ''.join(markdown_pattern.findall(response)) or response

    file_name = f"post_{data['id']}.md"
    with open(f"posts/{file_name}", "w", encoding="utf-8") as f:
        f.write(post)

    log_main.info(f"Contenido guardado en archivo {file_name}")

    new_post = database.Posts(
        id=data["id"],
        title=data["name"],
        description=data["description"],
        created_at=isoparse(data["created_at"]),
        updated_at=isoparse(data["updated_at"]),
        article=post
    )

    return new_post


@app.post("/posts", response_class=JSONResponse)
async def gen_post(data: dict):
    new_post = await generate_post_logic(data)

    if database.get_post(data["id"]) is None:
        database.save_post(new_post)

    return new_post


@app.put("/posts/{repo_id}")
async def update_post(repo_id: int):
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


@app.get("/posts/{repo_id}")
async def get_post(repo_id: int):
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
        return {"error": "Post not found"}


@app.post("/repos/update")
async def update_repos():
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


@app.post("/repos")
async def set_repos():
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


@app.get("/repos/{repo_id}")
async def get_repo(repo_id: int):
    repo = database.get_repo(repo_id)
    if repo:
        return repo

    else:
        return {"error": "Repository not found"}


@app.get("/repos")
async def get_repos():
    repos = database.get_repos()
    return repos


@app.get("/health", response_class=PlainTextResponse)
async def health():
    return "ok"


if __name__ == "__main__":
    uvicorn.run("main:app",
                host="0.0.0.0",
                port=3000,
                reload=True,
                log_config=LOGGING_CONFIG)