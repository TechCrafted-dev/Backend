import re
import json
import httpx
import requests

from typing import Any
from enum   import Enum, auto

from dateutil.parser import isoparse
from datetime import datetime, timedelta

from sqlalchemy.exc import IntegrityError

from modules import database
from modules.config import log_techAI, settings

from openai import AsyncOpenAI, RateLimitError
from openai.types.responses import ResponseOutputMessage, ResponseOutputText


API_KEY = settings['OPENAI']['API-KEY']

# ---------- OPENAI -------------
aclient = AsyncOpenAI(api_key=API_KEY)
MAX_TOKENS = 8192
CAPABILITIES = {
    "chat":     {"model": "gpt-4o", "max_output_tokens": True,  "tool_choice": True, "search": False, "reasoner": False},
    "find":   {"model": "gpt-4o", "max_output_tokens": True,  "tool_choice": True, "search": True, "reasoner": False},
    "search": {"model": "o4-mini", "max_output_tokens": False, "tool_choice": False, "search": True, "reasoner": True},
    "reasoner": {"model": "o4-mini", "max_output_tokens": False, "tool_choice": False, "search": False, "reasoner": True},
    "research": {"model": "o4-mini-deep-research", "max_output_tokens": False, "tool_choice": False, "search": True, "reasoner": False},
}


# ---------- UTILS ----------
def _extract_json(text: str) -> dict | Any:
    match = re.search(r'```json\n(.*?)\n```', text, re.DOTALL)

    try:
        if match:
            # Cargar el JSON extraído
            json_str = match.group(1)
            return json.loads(json_str)

        else:
            # Si no hay bloque JSON, intentar cargar directamente el string como JSON
            news_data = json.loads(text)
            return news_data

    except json.JSONDecodeError:
        log_techAI.warning("El LLM no devolvió un JSON válido.")

    except Exception as e:
        log_techAI.error("Error obteniendo noticias: %s", e)

    return {}


def build_kwargs(*, config: str, system: str, user: str):
    caps = CAPABILITIES[config]
    kwargs = {
        "model": caps["model"],
        "input": [
            {"role": "system", "content": [{"type": "input_text", "text": system}]},
            {"role": "user", "content": [{"type": "input_text", "text": user}]},
        ],
        "text": {"format": {"type": "text"}},
    }

    # TOKENS
    if caps.get("max_output_tokens"):
        kwargs["max_output_tokens"] = MAX_TOKENS

    # BUSCADOR
    if caps.get("search"):
        kwargs["tools"] = [{
            "type": "web_search_preview",
            "search_context_size": "high" if config == "search" else "medium",
            "user_location": {"type": "approximate"} if config == "search" else None
        }]

        if caps.get("tool_choice"):
            kwargs["tool_choice"] = "required"

    # RAZONADOR
    elif caps.get("reasoner"):
        kwargs["reasoning"] = {
            "effort": "medium"
        }

    return kwargs


# ---------- HELPERS ----------
async def _chat(system: str, user: str) -> str:
    try:
        response = await aclient.chat.completions.create(
            model="gpt-4o",
            temperature=0.7,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ]
        )

        return response.choices[0].message.content

    except Exception as e:
        log_techAI.error("Error durante la ejecución de chat completion: %s", e)
        raise


async def _response(payload: dict):
    try:
        response = await aclient.responses.create(**payload)
        return response

    except RateLimitError as e:
        log_techAI.error("Error de límite de tasa: %s", e)
        raise

    except Exception as e:
        log_techAI.error("Error durante la ejecución de responses: %s", e)
        raise


# ---------- TOOLS ----------
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


# - Analiza el repo y genera puntos clave [_chat]
async def tool_analyze_repo(repo_meta: dict, readme: str) -> str:
    log_techAI.info("Analizando repositorio...")

    sys = (
        "Eres un desarrollador que revisa su propio repositorio para preparar un post. "
        "Hablas siempre en primera persona singular."
    )

    user = (
        "Estos son los METADATOS de mi repositorio y su README sin procesar.\n\n"
        "======== METADATOS ========\n"
        f"{json.dumps(repo_meta, ensure_ascii=False, indent=2)}\n\n"
        "======== README ========\n"
        f"{readme[:800]}\n\n" # recorta a 8k  tokens approx 
        "----\n\n"
        "1⃣ Resúmeme en bullet-points (máx 10) qué hace el proyecto.\n"
        "2⃣ Destaca cuál es el problema que resuelve y a quién beneficia."
    )

    try:
        analysis = await _chat(sys, user)
        return analysis

    except Exception as e:
        log_techAI.error("Error analizando el repositorio: %s", e)
        raise


# - Genera un outline basado en los puntos clave [_chat]
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
        response = await _chat(sys, user)
        json_pattern = re.compile(r'```json\n(.*?)```', re.DOTALL)
        outline = ''.join(json_pattern.findall(response)) or response
        return outline

    except Exception as e:
        log_techAI.error("Error generando el outline: %s", e)
        raise


# - Escribe el post completo en Markdown [_response][reasoner]
async def tool_write_post(outline_json: str, repo_meta: dict, readme: str) -> str:
    log_techAI.info("Escribiendo el post completo...")
    sys = (
        "Eres el autor del repositorio, escribiendo un post profesional en primera persona. "
        "Estilo directo, cercano, con ejemplos de uso cuando proceda."
    )

    user = (
        "=== OUTLINE (JSON) ===\n"
        f"{outline_json}\n\n"
        
        "=== METADATOS ===\n"
        f"{json.dumps(repo_meta, ensure_ascii=False, indent=2)}\n\n"
        
        "=== README (recortado) ===\n"
        f"{readme[:4000]}\n\n"
        
        "- Redacta el artículo completo en Markdown.\n"
        "- Cada subtítulo del outline debe ser un encabezado H2.\n"
        "- Incluye fragmentos de código relevantes si aportan valor.\n"
        "- Mantén entre 400 y 800 palabras.\n"
        "- Termina con una línea horizontal `---` y un call-to-action invitando a visitar el repo y enviar feedback.\n"
    )

    try:
        response = await _response(build_kwargs(config="reasoner", system=sys, user=user))

        data = None
        for entry in response.output:
            if isinstance(entry, ResponseOutputMessage) or entry.type == "message":
                for chunk in entry.content:
                    if isinstance(chunk, ResponseOutputText) or chunk.type == "output_text":
                        data = chunk.text

        return data

    except Exception as e:
        log_techAI.error("Error escribiendo el post: %s", e)
        raise


# - Limpia el Markdown final [_chat]
async def tool_markdown_polish(draft_md: str) -> str:
    log_techAI.info("Depurando el Markdown final...")
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


# - Obtiene enlaces de proveedores de noticias más importantes [_response][search]
async def tool_source_news() -> list:
    log_techAI.info("Obteniendo enlaces de fuentes de noticias...")

    sys = (
        "Eres un asistente que busca y proporciona enlaces de fuentes de noticias de programación.\n"
        "Asegurate de que las URLs son relevantes y actualizadas.\n"
        "Descarta aquellas fuentes que no estén al día.\n\n"
        
        "Siempre devuelve una lista de enlaces en formato JSON con la siguiente estructura:\n"
        "{'sources': ['url1', 'url2', ...]}\n\n"
        
        "URLs vetadas que no debes agregar:\n"
        " - https://www.noticias.dev"
    )
    user = "Proporciona una lista de fuentes de noticias relacionadas con la programación."

    response = await _response(build_kwargs(config="find", system=sys, user=user))
    data = None
    for entry in response.output:
        if isinstance(entry, ResponseOutputMessage) or entry.type == "message":
            for chunk in entry.content:
                if isinstance(chunk, ResponseOutputText) or chunk.type == "output_text":
                    data = chunk.text

    sources = _extract_json(data)
    return sources.get('sources', [])


# - Obtiene noticias de las fuentes proporcionadas [_response][search]
async def tool_get_news(sources: list) -> dict:
    log_techAI.info(f"Obteniendo noticias de {len(sources)} fuentes:")

    model = {
            "title": "Titulo de la noticia",
            "url": "URL de la noticia",
            "date": "YYYY-MM-DD",
    }

    sys = (
        "Eres un asistente que recopila noticias tecnológicas de las fuentes "
        "proporcionadas, con énfasis en programación (Python, Java, JavaScript, "
        "TypeScript, Go, Rust, etc.).\n\n"

        f"Hoy es {datetime.now().strftime('%d de %B del %Y')}.\n"
        "Considera únicamente las noticias publicadas esta semana.\n\n"

        "- Analiza únicamente los titulares, no profundices en el contenido completo.\n"
        "- Traduce los títulos al español si están en otro idioma.\n"
        "- Descarta artículos que sean notas de prensa, ofertas de empleo, "
        "eventos o contenido puramente comercial.\n"
        "- Prioriza lanzamientos de versiones, vulnerabilidades críticas, nuevos "
        "frameworks o herramientas relevantes para desarrolladores.\n\n"
        "- No inventes información, usa únicamente la fuente dada.\n"

        "Devuelve tu respuesta **exclusivamente** como una lista JSON con la "
        "estructura siguiente (sin texto adicional):\n"
        f"{json.dumps(model, ensure_ascii=False, indent=2)}\n\n"

        "Si no encuentras noticias relevantes, devuelve un JSON con una lista "
        "vacía: `[]`.\n"
    )

    news = {}
    count = 1
    for source in sources:
        log_techAI.info(f"{count}: {source}")
        count += 1

        user = (
            "Recopila noticias de programación.\n"
            f"Aquí tienes la URL de la fuente: {source}."
        )

        try:
            response = await _response(build_kwargs(config="find", system=sys, user=user))

            content = None
            for entry in response.output:
                if isinstance(entry, ResponseOutputMessage) or entry.type == "message":
                    for chunk in entry.content:
                        if isinstance(chunk, ResponseOutputText) or chunk.type == "output_text":
                            content = chunk.text

            log_techAI.info(content)
            content = _extract_json(content)

        except Exception as e:
            log_techAI.error("Error obteniendo noticias de %s: %s", source, e)
            content = []

        news[source] = content
        log_techAI.info(f"Noticias obtenidas: {len(content)}")

    return news


# - Clasifica las noticias más relevantes [_response][reasoner]
async def tool_cleanup_news(news_sources: dict) -> list:
    log_techAI.info("Limpiando y clasificando noticias...")

    model = [{
        "title": "Titulo de la noticia en español",
        "date": "YYYY-MM-DD",
        "language": "Lenguaje de programación relacionado (Python, Java, etc.)",
        "source": "URL fuente de la noticia",
        "url": "URL de la noticia"
    }]

    sys = (
        'Eres un asistente que organiza noticias tecnológicas.'
        'Devuelve un JSON con la siguiente estructura:'
        f'{json.dumps(model, ensure_ascii=False, indent=2)}\n'
    )

    today = datetime.today().date()
    cutoff = today - timedelta(days=7)

    clear_news = []
    for site, articles in news_sources.items():
        if not articles:
            continue

        recientes = [
            art for art in articles
            if datetime.strptime(art["date"], "%Y-%m-%d").date() >= cutoff
        ]

        if not recientes:
            continue

        news = {"source": site, "news": []}
        for article in articles:
            news["news"].append(article)

        log_techAI.info("Fuente: %s", site)

        user = (
            "Analiza atentamente las noticias proporcionadas."
            "Deben estar relacionadas con programación: Python, Java, JavaScript, etc."
            "Descarta aquellas que no aporten valor, que sean irrelevantes o que estén duplicadas."
            "Prioriza lanzamientos de versiones, vulnerabilidades críticas, nuevos "
            "frameworks o herramientas relevantes para desarrolladores"
            f"\n{json.dumps(news, ensure_ascii=False, indent=2)}"
        )

        try:
            response = await _response(build_kwargs(config="reasoner", system=sys, user=user))
            data = None
            for entry in response.output:
                if isinstance(entry, ResponseOutputMessage) or entry.type == "message":
                    for chunk in entry.content:
                        if isinstance(chunk, ResponseOutputText) or chunk.type == "output_text":
                            data = chunk.text

            clear_news.extend(_extract_json(data))

        except Exception as e:
            log_techAI.error("Error limpiando noticias: %s", e)
            raise

    total_news = sum(len(articles) for articles in news_sources.values())
    log_techAI.info("Eran %s noticias, quedan %s tras la limpieza.", total_news, len(clear_news))
    return clear_news


# - Redacta las noticias en formato Markdown [_response][search]
async def tool_redactor(news: list) -> list:
    log_techAI.info("Redactando las noticias...")
    sys = (
        "Eres un redactor profesional que escribe artículos de noticias tecnológicas.\n"
        "Usa la fuente y la URL de la noticia para proporcionar contexto.\n"
        "Utiliza un tono directo y profesional, pero cercano.\n"
        "Devuelve el resultado en formato Markdown.\n\n"

        "Al final del artículo, incluye una línea horizontal `---` e invita a visitar la pagina de la noticia.\n\n"

        "No incluyas ni fechas ni urls en el artículo.\n"
        "No inventes información, usa únicamente los datos proporcionados.\n"
        "Si la URL de la noticia no es válida, descártala respondiendo únicamente None."
    )

    final_news = []
    for news_item in news:
        log_techAI.info(f"URL: {news_item['url']}")
        user = (
            f"### {news_item['title']}\n"
            f"- **Fecha:** {news_item['date']}\n"
            f"- **Lenguaje:** {news_item['language']}\n"
            f"- **Fuente:** [{news_item['source']}]"
            f"- **Url:** ({news_item['url']})\n"
        )

        try:
            response = await _response(build_kwargs(config="find", system=sys, user=user))
            data = None
            for entry in response.output:
                if isinstance(entry, ResponseOutputMessage) or entry.type == "message":
                    for chunk in entry.content:
                        if isinstance(chunk, ResponseOutputText) or chunk.type == "output_text":
                            data = chunk.text

            # Si None descartar
            if data in (None, "None"):
                log_techAI.info("Descartada por irrelevante o duplicada")
                continue

            # Extraer o dejar tal cual
            markdown_pattern = re.compile(r"```(?:markdown)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)
            match = markdown_pattern.search(data) if isinstance(data, str) else None
            summary = match.group(1).strip() if match else str(data).strip()

            # Guardar
            news_item_with_summary = news_item.copy()
            news_item_with_summary["summary"] = summary
            final_news.append(news_item_with_summary)


        except Exception as e:
            log_techAI.error("Error redactando las noticias: %s", e)
            raise

    return final_news


async def source_news(sources):
    log_techAI.info("Obteniendo enlaces de fuentes de noticias...")

    model = """
    {
      "news_sources": [
        {
          "url1": "https://example.com/rss.xml",
          "url2": "https://example.org/feed.atom"
        }
      ]
    }"""

    sys = (
        "Eres un asistente experto en programación y seguridad informática. "
        "Tu tarea es encontrar y devolver **únicamente URLs de feeds RSS o Atom** "
        "con noticias de programación RELEVANTES y ACTUALIZADAS.\n\n"

        "## Requisitos del resultado\n"
        "• Responde **SOLO** con JSON válido, sin texto adicional, "
        "y siguiendo exactamente la estructura:\n"
        f"{model}\n\n"

        "## Criterios de calidad para aceptar una fuente\n"
        "1. Debe ser un feed RSS/Atom accesible (HTTP 200) y bien formado.\n"
        "2. Debe publicar changelogs, lanzamientos, vulnerabilidades o artículos técnicos "
        "directamente relacionados con lenguajes (Python, Java, JavaScript, TypeScript, Go, Rust, Kotlin, etc...), "
        "frameworks (React, Spring, Angular, Astro, etc...).\n"
        "3. Da prioridad a **blogs oficiales** del lenguaje, "
        "avances en estándares (IETF, W3C) y listas de correo convertidas a RSS.\n"
        "4. Acepta también blogs de seguridad o laboratorios de proveedores "
        "que publiquen CVE y parches relevantes para desarrolladores.\n\n"

        "## Filtros de exclusión (descarta si se cumple CUALQUIERA)\n"
        "• Agregadores genéricos (Medium, Reddit, Hacker News, Dev.to, Substack personal, etc...).\n"
        "• Blogs puramente comerciales o de marketing, notas de prensa, patrocinios, webinars.\n"
        "• Anuncios de empleo, eventos, meetups, conferencias.\n"
        "• Feeds que ya estén listados en «URLs almacenadas» o «URLs vetadas» (véase abajo).\n"
        "• Duplicados exactos o variantes http/https, con o sin www.\n\n"

        "## Formato estricto\n"
        "• Usa siempre HTTPS si está disponible.\n"
        "• No incluyas más de un feed por dominio a menos que cubra proyectos distintos "
        "y claramente diferenciados.\n\n"

        "### URLs almacenadas que NO debes incluir nuevamente:\n"
    )

    # Añade las listas dinámicas de `sources` y `vetoed`:
    sys += "\n".join(f"- {source.url}" for source in sources)
    sys += (
        "\n\n"
        "### Recordatorio final\n"
        "• Intenta tener una lista rica de contenido, no repitas temáticas\n."
        "• Centrate sobre todo en lenguajes de programación y frameworks."
        "• Devuelve **exclusivamente** el JSON pedido.\n"
        "• No incluyas comentarios, explicaciones ni código adicional.\n"
    )

    user = (
        "Proporciona una lista de entre 10 o 20 fuentes de noticias relacionadas con la programación.\n"
    )

    response = await _response(build_kwargs(config="find", system=sys, user=user))
    data = None
    for entry in response.output:
        if isinstance(entry, ResponseOutputMessage) or entry.type == "message":
            for chunk in entry.content:
                if isinstance(chunk, ResponseOutputText) or chunk.type == "output_text":
                    data = chunk.text

    sources = _extract_json(data)
    return sources.get('news_sources', [])


async def source_rss(sources: list) -> dict:
    log_techAI.info(f"Normalizando RSS de {len(sources[0])} fuentes:")

    model = {
        "Nombre de la fuente": {
            "url": "url canónico de la fuente",
            "rss": "url del rss o feed"
        }
    }

    sys = (
        "Eres un extractor de metadatos RSS.\n\n"
        
        "Para **cada feed** que te entregue el usuario:\n"
        "1. Descarga el feed (HTTP 200 obligatorio). Si falla, pon \"rss\": \"None\".\n"
        "2. Obtén el <title> del canal o, si falta, el <title> de la página HTML.\n"
        "   Usa ese texto —sin las palabras 'RSS', 'Feed' ni 'Atom'— como nombre legible.\n"
        "3. Deriva la URL de la home quitando la ruta del feed.\n"
        "4. Devuelve un único objeto JSON con el siguiente formato.\n"
        f"{json.dumps(model, ensure_ascii=False, indent=2)}\n\n"

        "Reglas extra:\n"
        "• Fuerza HTTPS siempre que exista.\n"
        "• No devuelvas dominios duplicados ni los listados en «URLs almacenadas»/«vetadas».\n"
        "• No añadas ningún texto fuera del JSON."
    )

    user = (
        "Extrae metadatos de estas URLs de feed:\n"
    )

    for source in sources:
        user += f"- {source}\n"

    response = await _response(build_kwargs(config="find", system=sys, user=user))
    data = None
    for entry in response.output:
        if isinstance(entry, ResponseOutputMessage) or entry.type == "message":
            for chunk in entry.content:
                if isinstance(chunk, ResponseOutputText) or chunk.type == "output_text":
                    data = chunk.text

    sources = _extract_json(data)

    return sources


async def validate_rss(sources: dict):
    log_techAI.info("Validando RSS...")

    for source, data in sources.items():
        try:
            resp = requests.get(data['rss'], timeout=10)

        except Exception as e:
            continue

        if resp.status_code == 200:
            log_techAI.info("Fuente %s disponible", source)

            try:
                new_source = database.NewsSource(
                    name=source,
                    url=data['url'],
                    rss=data['rss'],
                    added_at=datetime.now(),
                    score=1
                )

                database.save_news_source(new_source)

            except IntegrityError as e:
                log_techAI.warning("Fuente ya almacenada: %s", source)

            except Exception as e:
                log_techAI.info("Error al guardar la fuente: %s", e)
                raise e


async def extract_news(sources):
    log_techAI.info(f"Extrayendo noticias de {len(sources)} fuentes...")

    sources = database.get_news_sources_by_score(0, "greater")

    today = datetime.now()
    seven_day = today - timedelta(days=7)

    model = {
        "title": "Título de la noticia en español",
        "url": "URL de la noticia",
        "date": "YYYY-MM-DD"
    }

    sys = (
        "Eres un asistente que recopila titulares tecnológicos centrados en programación "
        "(Python, Java, JavaScript, TypeScript, Go, Rust, etc.) a partir de fuentes RSS proporcionadas.\n\n"

        f"Hoy es {today.strftime('%d de %B de %Y')}.\n"
        f"Analiza exclusivamente las noticias publicadas ENTRE {seven_day.strftime('%Y-%m-%d')} "
        f"y {today.strftime('%Y-%m-%d')} (últimos 7 días, inclusive).\n\n"

        "REGLAS DE FILTRADO\n"
        "• Usa SOLO el título y la fecha del ítem RSS; no abras el artículo.\n"
        "• Traduce el título al español si está en otro idioma.\n"
        "• Descarta notas de prensa, anuncios de empleo, eventos o contenido puramente comercial.\n"
        "• Prioriza versiones nuevas, vulnerabilidades críticas, frameworks o herramientas útiles para desarrolladores.\n"
        "• No inventes datos: si un campo no existe o falta la fecha, descarta el ítem.\n\n"

        "FORMATO DE RESPUESTA\n"
        "• Devuelve ÚNICAMENTE una lista JSON (sin texto adicional) con la forma exacta del modelo siguiente.\n"
        f"{json.dumps(model, ensure_ascii=False, indent=2)}\n\n"
        "• Si no hay noticias válidas, responde una lista vacia: []\n"
    )

    news_week = []
    count = 1
    for source in sources:
        user = (
            "Recopila noticias de programación de los últimos 7 días.\n"
            f"Fuente RSS: {source.rss}\n"
        )

        log_techAI.info(f"({count}/{len(sources)}) {source.name}")
        count += 1

        response = await _response(build_kwargs(config="search", system=sys, user=user))
        data = None
        for entry in response.output:
            if isinstance(entry, ResponseOutputMessage) or entry.type == "message":
                for chunk in entry.content:
                    if isinstance(chunk, ResponseOutputText) or chunk.type == "output_text":
                        data = chunk.text

        resources = _extract_json(data)
        if len(resources) != 0:
            log_techAI.info("Respuesta:\n%s", resources)
            resources[0]["source"] = {
                "name": source.name,
                "url": source.url,
                "rss": source.rss,
            }

            news_week.extend(resources)

    log_techAI.info("Respuesta:\n%s", news_week)
    return news_week


async def gen_news(news_week):
    log_techAI.info(f"Generando publicaciones de {len(news_week)} noticias.")

    model = {
        "sumary": {
            "introduction": "Entradilla",
            "content": "Contenido"
        }
    }

    sys = (
        "Eres un redactor técnico especializado. "
        "Debes acceder a la URL, leer la fuente original y generar un post compuesto por dos partes:\n"
        " • Entradilla: un párrafo breve y atractivo que resuma el anuncio.\n"
        " • Contenido: desarrollo con contexto, detalles, cambios clave y por qué importa.\n\n"
        
        "Reglas de calidad:\n"
        " • Nada de inventar, todo debe venir de la fuente o de páginas oficiales enlazadas desde ella.\n"
        " • Siempre visita la URL dada. Si la página no carga, omite el artículo.\n"
        " • Citas textuales, si las usas, máximo 20 palabras por cita.\n"
        " • Estilo claro, conciso, neutral, ligeramente divulgativo.\n"
        " • Entradilla: 45–80 palabras.\n"
        " • Contenido ampliado: 300–600 palabras, con subtítulos si aporta claridad.\n"
        " • No añadas opiniones, sólo contexto comprobable.\n\n"

        "Método de salida:\n"
        " • Debe ser **únicamente** en formato JSON.\n"
        " • No agreges comentarios y texto adicional.\n"
        " • Usa la siguiente estructura:\n"
        f"{json.dumps(model, ensure_ascii=False, indent=2)}\n"
    )


    posts_news = []
    for news in news_week:
        user = (
            "Genera un post de la siguiente url dada:\n"
        )

        user += f"{news.url}\n"

        response = await _response(build_kwargs(config="search", system=sys, user=user))
        data = None
        for entry in response.output:
            if isinstance(entry, ResponseOutputMessage) or entry.type == "message":
                for chunk in entry.content:
                    if isinstance(chunk, ResponseOutputText) or chunk.type == "output_text":
                        data = chunk.text

        summary = _extract_json(data)
        log_techAI.info("Respuesta:\n%s", summary)
        news["sumary"] = summary[0]["sumary"]
        posts_news.append(news)

    return posts_news


# ---------- PIPELINES ----------
class Pipeline(Enum):
    TEST = auto()     # Para pruebas
    EVAL = auto()     # Para comprobar si ha cambiado
    POST = auto()     # Para generar posts
    NEWS = auto()     # Para obtener noticias


async def _run_pipeline(data: dict, mode: Pipeline) -> str | list | None:
    log_techAI.info("Ejecutando el pipeline en modo: %s", mode.name)

    if mode is Pipeline.TEST:
        sources = database.get_news_sources_by_score(0, "greater")
        if  len(sources) < 50:
            find_sources = await source_news(sources)
            get_rss = await source_rss(find_sources)
            await validate_rss(get_rss)

        news_week = await extract_news(sources)
        posts_news = await gen_news(news_week)
        log_techAI.info("listado de news:\n%s", posts_news)

    if mode is Pipeline.EVAL:
        last_date = isoparse(data['updated_at'])
        if last_date > datetime.now() - timedelta(days=7):
            log_techAI.warning("El repositorio ha sido actualizado recientemente.")
            mode = Pipeline.POST

        else:
            log_techAI.info("No es necesario actualizar el Post.")

    if mode is Pipeline.POST:
        readme = await tool_fetch_readme(data)
        analysis = await tool_analyze_repo(data, readme)
        outline = await tool_generate_outline(analysis)
        post = await tool_write_post(outline, data, readme)
        cleaner = await tool_markdown_polish(post)
        return cleaner

    if mode is Pipeline.NEWS:
        sources = await tool_source_news()
        news = await tool_get_news(sources)
        cleaner = await tool_cleanup_news(news)
        sort = sorted(cleaner, key=lambda x: datetime.strptime(x['date'], '%Y-%m-%d'))
        redactor = await tool_redactor(sort)
        return redactor

    return None

# ---------- TEST ----------
async def test_pipeline(mode: Pipeline) -> list:
    log_techAI.info("Ejecutando el pipeline de prueba...")

    response = await _run_pipeline({}, mode)
    log_techAI.info("Pipeline de prueba completado con éxito.")


# ---------- GENERATE POST ----------
async def gen_post(data, mode: Pipeline) -> str:
    log_techAI.info("Generando post...")

    try:
        data = data if isinstance(data, dict) else json.loads(data)
        response = await _run_pipeline(data, mode)

        if response is None:
            log_techAI.info("Post generado con éxito.")

        return response

    except Exception as e:
        log_techAI.error("Error generando el post: %s", e)
        raise


# ---------- GET NEWS ----------
async def get_news(mode: Pipeline) -> list:
    try:
        response = await _run_pipeline({}, mode)
        log_techAI.info(response)
        return response

    except Exception as e:
        log_techAI.error("Error obteniendo noticias: %s", e)
        raise