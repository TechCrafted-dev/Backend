import json
import re

import httpx

from enum   import Enum, auto
from openai import AsyncOpenAI
from config import log_techAI, OPENAI_API_KEY


# ---------- OPENAI -------------
aclient = AsyncOpenAI(api_key=OPENAI_API_KEY)
MODEL = "gpt-4o-mini"
TEMP  = 0.7

# ---------- HELPERS ------------
async def _chat(system: str, user: str) -> str:
    try:
        response = await aclient.chat.completions.create(
            model       = MODEL,
            temperature = TEMP,
            messages    = [
                {"role": "system", "content": system},
                {"role": "user",   "content": user }
            ]
        )

        return response.choices[0].message.content

    except Exception as e:
        log_techAI.error("Error durante la ejecución de chat completion: %s", e)
        raise


# ========== TOOLS ==========
# - Obtiene README del repo
async def tool_fetch_readme(repo_meta: dict) -> str:
    log_techAI.info("Obteniendo README...")

    try:
        url = repo_meta.get("url", "")
        if not url:
            return ""

        owner_repo = "/".join(url.rstrip("/").split("/")[-2:])
        candidates = [
            f"https://raw.githubusercontent.com/{owner_repo}/HEAD/README.md",
            f"https://raw.githubusercontent.com/{owner_repo}/HEAD/README.rst",
            f"https://raw.githubusercontent.com/{owner_repo}/HEAD/README"
        ]

        async with httpx.AsyncClient(timeout=10) as client:
            for raw_url in candidates:
                try:
                    r = await client.get(raw_url)
                    if r.status_code == 200 and len(r.text.strip()) > 20:
                        return r.text

                except httpx.RequestError:
                    pass

        log_techAI.warning("No se encontró un README válido en las URLs candidatas.")
        return ""

    except Exception as e:
        log_techAI.error("Error obteniendo README: %s", e)
        raise


# - Analiza el repo y genera puntos clave
async def tool_analyze_repo(repo_meta: dict, readme: str) -> str:
    log_techAI.info("Analizando repositorio...")

    sys = (
        "Eres un desarrollador que revisa su propio repositorio para preparar un post. "
        "Hablas siempre en primera persona singular."
    )
    user = f"""
Estos son los METADATOS de mi repositorio y su README sin procesar.
======== METADATOS ========
{json.dumps(repo_meta, ensure_ascii=False, indent=2)}
======== README ========
{readme[:4000]}  <!-- recorta a 4 k tokens aprox -->
----
1⃣ Resúmeme en bullet-points (máx 10) qué hace el proyecto.
2⃣ Destaca cuál es el problema que resuelve y a quién beneficia.
"""

    try:
        analysis = await _chat(sys, user)
        return analysis

    except Exception as e:
        log_techAI.error("Error analizando el repositorio: %s", e)
        raise


# - Genera un outline basado en los puntos clave
async def tool_generate_outline(key_points: str) -> str:
    log_techAI.info("Generando outline del artículo...")
    sys = "Eres un copywriter técnico que estructura artículos en Markdown."
    user = f"""
Con base en los siguientes puntos clave, diseña una estructura Markdown:
{key_points}

✅ Devuelve JSON con:
- title: string (máx 80 carac, primera persona)
- sections: array[str] (subtítulos H2 en orden lógico, 3-6 elementos)
"""
    try:
        # function-calling opcional; aquí devolvemos texto JSON
        response = await _chat(sys, user)
        json_pattern = re.compile(r'```json\n(.*?)```', re.DOTALL)
        outline = ''.join(json_pattern.findall(response)) or response
        return outline

    except Exception as e:
        log_techAI.error("Error generando el outline: %s", e)
        raise


# - Escribe el post completo en Markdown
async def tool_write_post(outline_json: str, repo_meta: dict, readme: str) -> str:
    log_techAI.info("Escribiendo el post completo...")
    sys = (
        "Eres el autor del repositorio, escribiendo un post profesional en primera persona. "
        "Estilo directo, cercano, con ejemplos de uso cuando proceda."
    )
    user = f"""
=== OUTLINE (JSON) ===
{outline_json}

=== METADATOS ===
{json.dumps(repo_meta, ensure_ascii=False, indent=2)}

=== README (recortado) ===
{readme[:4000]}

- Redacta el artículo completo en Markdown.
- Cada subtítulo del outline debe ser un encabezado H2.
- Incluye fragmentos de código relevantes si aportan valor.
- Mantén entre 400 y 800 palabras.
- Termina con una línea horizontal `---` y un call-to-action invitando a visitar el repo y enviar feedback.
"""
    try:
        post = await _chat(sys, user)
        return post

    except Exception as e:
        log_techAI.error("Error escribiendo el post: %s", e)
        raise


# - Limpia el Markdown final
async def tool_markdown_polish(draft_md: str) -> str:
    log_techAI.info("Limpiando el Markdown final...")
    sys = (
        "Eres un corrector de estilo Markdown. "
        "Corrige formatos (encabezados, listas, code-blocks) sin cambiar el contenido."
    )
    user = draft_md
    cleaned = await _chat(sys, user)

    # Asegura la línea separatoria + CTA
    if not re.search(r"^---\s*$", cleaned, flags=re.M):
        cleaned += "\n\n---\n¡Si te gusta el proyecto, pásate por el repo y deja tu feedback! ⭐️"

    return cleaned


# ---------- PIPELINES ----------
class Pipeline(Enum):
    TEST = auto()  # Para pruebas unitarias

async def run_pipeline(data: dict, mode: Pipeline) -> str:
    log_techAI.info("Ejecutando el pipeline en modo: %s", mode.name)
    try:
        if mode is Pipeline.TEST:
            readme = await tool_fetch_readme(data)
            analysis = await tool_analyze_repo(data, readme)
            outline = await tool_generate_outline(analysis)
            post = await tool_write_post(outline, data, readme)
            clear = await tool_markdown_polish(post)
            return clear

    except Exception as e:
        log_techAI.error("Error ejecutando el pipeline: %s", e)
        raise


# ---------- GENERATE POST -------
async def gen_post(data: dict, mode: Pipeline = Pipeline.TEST) -> str:
    log_techAI.info("Generando post...")

    try:
        data = data if isinstance(data, dict) else json.loads(data)
        response = await run_pipeline(data, mode)
        log_techAI.info("Post generado con éxito.")
        return response

    except Exception as e:
        log_techAI.error("Error generando el post: %s", e)
        raise
