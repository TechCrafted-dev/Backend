import json
import requests

from config import log_github, GITHUB_USERNAME, GITHUB_TOKEN


# Encabezados para la autenticación
HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28"
}


# Obtener datos del usuario
def get_user_info():
    url = f"https://api.github.com/users/{GITHUB_USERNAME}"
    response = requests.get(url, headers=HEADERS)

    if response.status_code == 200:
        log_github.info("Información del usuario obtenida correctamente.")
        return response.json()

    else:
        log_github.error(f"Error al obtener la información del usuario. Código: {response.status_code}")
        return {}


# Obtener la lista de repositorios del usuario
def get_repositories():
    log_github.info("Fetching user information...")

    url = f"https://api.github.com/users/{GITHUB_USERNAME}/repos?per_page=100"
    response = requests.get(url, headers=HEADERS)
    data = response.json()

    if response.status_code == 200:
        log_github.info("Información del usuario obtenida correctamente.")
        return data
    else:
        log_github.error(f"Error al obtener la información del usuario. Código: {response.status_code}")
        return {}


# Obtener estadísticas de tráfico (vistas y clones) de un repositorio
def get_repo_traffic(repo_name):
    log_github.info(f"Fetching traffic for {repo_name}...")
    base_url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{repo_name}/traffic"

    url_views = f"{base_url}/views"
    url_clones = f"{base_url}/clones"

    views_response = requests.get(url_views, headers=HEADERS)
    clones_response = requests.get(url_clones, headers=HEADERS)

    views = views_response.json() if views_response.status_code == 200 else {}
    clones = clones_response.json() if clones_response.status_code == 200 else {}

    return {
        "views": views.get("count", 0),
        "unique_views": views.get("uniques", 0),
        "clones": clones.get("count", 0),
        "unique_clones": clones.get("uniques", 0)
    }


# Recopilar datos de los repositorios
def get_repos_data(order_by="created_at", reverse=True):
    repos = get_repositories()
    repos_data = []

    for repo in repos:
        repo_name = repo["name"]
        traffic = get_repo_traffic(repo_name)

        log_github.info(f"Traffic for {repo_name}")

        repo_info = {
            "id": repo["id"],
            "name": repo_name,
            "description": repo["description"] if repo["description"] else "No description available",
            "url": repo["html_url"],
            "language": repo["language"] if repo["language"] else "Unknown",
            "stars": repo["stargazers_count"],
            "forks": repo["forks_count"],
            "watchers": repo["watchers_count"],
            "views": traffic["views"],
            "unique_views": traffic["unique_views"],
            "clones": traffic["clones"],
            "unique_clones": traffic["unique_clones"],
            "created_at": repo["created_at"],
            "updated_at": repo["pushed_at"],
        }

        repos_data.append(repo_info)

    # Ordenar los repositorios según el criterio elegido
    key = order_by if order_by in ["stars", "views", "clones", "created_at", "updated_at"] else "created_at"
    repos_data.sort(key=lambda x: x[key], reverse=reverse)

    return repos_data
