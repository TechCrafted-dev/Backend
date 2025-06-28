
import json
import base64
import requests


# Cargar credenciales desde config.json
with open("config.json", "r") as config_file:
    config = json.load(config_file)

GITHUB_USERNAME = config["GITHUB_USERNAME"]
GITHUB_TOKEN = config["GITHUB_TOKEN"]

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
    return response.json() if response.status_code == 200 else {}


# Obtener la lista de repositorios del usuario
def get_repositories():
    url = f"https://api.github.com/users/{GITHUB_USERNAME}/repos?per_page=100"
    response = requests.get(url, headers=HEADERS)
    data = response.json()

    # Guardar los datos sin procesar para análisis
    with open("raw_github_data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    return data if response.status_code == 200 else []


# Obtener estadísticas de tráfico (vistas y clones) de un repositorio
def get_repo_traffic(repo_name):
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


# Recopilar datos de los repositorios con lenguaje de programación incluido
def get_repos_data(order_by="created_at", reverse=True):
    repos = get_repositories()
    repos_data = []

    for repo in repos:
        repo_name = repo["name"]
        traffic = get_repo_traffic(repo_name)

        repo_info = {
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
            "updated_at": repo["updated_at"]
        }

        repos_data.append(repo_info)

    # Ordenar los repositorios según el criterio elegido
    key = order_by if order_by in ["stars", "views", "clones", "created_at", "updated_at"] else "created_at"
    repos_data.sort(key=lambda x: x[key], reverse=reverse)

    return repos_data

def get_readme(repo_full_name):
    """Devuelve el contenido del README.md decodificado de un repositorio"""
    url = f"https://api.github.com/repos/{repo_full_name}/readme"
    response = requests.get(url, headers=HEADERS)

    if response.status_code == 200:
        content = response.json()["content"]
        decoded = base64.b64decode(content).decode("utf-8")
        return decoded
    else:
        print(f"No se pudo obtener README de {repo_full_name}: {response.status_code}")
        return None

# Obtener los datos del usuario y repositorios ordenados
user_info = get_user_info()
repos_data = get_repos_data(order_by="created_at", reverse=True)  # Ahora ordena por fecha de creación por defecto

# Estructurar el JSON final
github_data = {
    "user": {
        "username": user_info.get("login", ""),
        "name": user_info.get("name", ""),
        "bio": user_info.get("bio", ""),
        "location": user_info.get("location", ""),
        "followers": user_info.get("followers", 0),
        "following": user_info.get("following", 0),
        "public_repos": user_info.get("public_repos", 0),
        "url": user_info.get("html_url", "")
    },
    "repositories": repos_data
}

# Guardar los datos en un archivo JSON
with open("github_data.json", "w", encoding="utf-8") as f:
    json.dump(github_data, f, indent=4, ensure_ascii=False)

print("Datos guardados en github_data.json y raw_github_data.json")
