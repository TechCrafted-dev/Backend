import re
import json
import httpx

from enum   import Enum, auto
from datetime import datetime, timedelta

from openai import AsyncOpenAI, RateLimitError
from openai.types.responses import ResponseOutputMessage, ResponseOutputText

from config import log_techAI, OPENAI_API_KEY


# ---------- OPENAI -------------
aclient = AsyncOpenAI(api_key=OPENAI_API_KEY)
MODEL = "gpt-4o"
TEMP  = 0.7
MAX_TOKENS = 8192
CAPABILITIES = {
    "chat":     {"model": "gpt-4o", "max_output_tokens": True,  "tool_choice": True, "search": False, "reasoner": False},
    "search":   {"model": "gpt-4o", "max_output_tokens": True,  "tool_choice": True, "search": True, "reasoner": False},
    "reasoner": {"model": "o4-mini", "max_output_tokens": False, "tool_choice": False, "search": False, "reasoner": True},
    "research": {"model": "o4-mini-deep-research", "max_output_tokens": False, "tool_choice": False, "search": True, "reasoner": False},
}


# ---------- UTILS ----------
def extract_json(text: str) -> dict:
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

    except json.JSONDecodeError as e:
        log_techAI.error("Error decodificando JSON de noticias: %s", e)

    except Exception as e:
        log_techAI.error("Error obteniendo noticias: %s", e)

    return []


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


# - Obtiene enlaces de proveedores de noticias más importantes
async def tool_source_news() -> str:
    log_techAI.info("Obteniendo enlaces de fuentes de noticias...")

    sys = (
        "Eres un asistente que proporciona enlaces de fuentes de noticias tecnológicas."
        "Siempre devuelve una lista de enlaces en formato JSON con la siguiente estructura:"
        "{'sources': ['url1', 'url2', ...]}"
        "Asegurate de que las URLs son relevantes y actualizadas."
        "Descarta aquellas fuentes que no estén al día."
        "No agregues mas de 3"
        "URLs vetadas que no debes agregar:"
        " - https://www.noticias.dev"
    )
    user = "Proporciona una lista de enlaces a las principales fuentes de noticias relacionadas con programación."
    response = await _response(build_kwargs(config="search", system=sys, user=user))

    msg = next(
        item for item in response.output
        if item.type == "message"
    )

    sources = msg.content[0].text
    sources = extract_json(sources)
    return sources.get('sources', [])


# - Obtiene noticias de las fuentes proporcionadas
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
    
        f"Hoy es {datetime.now().strftime('%d de %B del %Y')}. "
        "Solo considera noticias publicadas en los últimos 7 días.\n\n"
    
        "- Analiza únicamente los titulares, no profundices en el contenido completo.\n"
        "- Traduce los títulos al español si están en otro idioma.\n"
        "- Descarta artículos que sean notas de prensa, ofertas de empleo, "
        "eventos o contenido puramente comercial.\n"
        "- Prioriza lanzamientos de versiones, vulnerabilidades críticas, nuevos "
        "frameworks o herramientas relevantes para desarrolladores.\n\n"
    
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
            f"Aquí tienes la URL de la fuente: {source}. "
            "Recopila las noticias según las instrucciones del system prompt."
)
        try:
            response = await _response(build_kwargs(config="search", system=sys, user=user))
            msg = next(
                item for item in response.output
                if item.type == "message"
            )

            content = msg.content[0].text.strip()
            content = extract_json(content)

        except Exception as e:
            log_techAI.error("Error obteniendo noticias de %s: %s", source, e)
            content = []

        news[source] = content
        log_techAI.info(f"Noticias obtenidas: {len(content)}")

    return news


# - Clasifica las noticias más relevantes
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

        user = ("Analiza atentamente las noticias proporcionadas."
                "Deben estar relacionadas con programación: Python, Java, JavaScript, etc."
                "Descarta aquellas que no aporten valor, que sean irrelevantes o que estén duplicadas."
                "Prioriza lanzamientos de versiones, vulnerabilidades críticas, nuevos "
                "frameworks o herramientas relevantes para desarrolladores"
                f"\n{json.dumps(news, ensure_ascii=False, indent=2)}")

        try:
            response = await _response(build_kwargs(config="reasoner", system=sys, user=user))
            msg = next(
                item for item in response.output
                if item.type == "message"
            )
            data = extract_json(msg.content[0].text)
            clear_news.extend(data)

        except Exception as e:
            log_techAI.error("Error limpiando noticias: %s", e)
            raise

    total_news = sum(len(articles) for articles in news_sources.values())
    log_techAI.info("Eran %s noticias, quedan %s tras la limpieza.", total_news, len(clear_news))
    return clear_news


# - Redacta las noticias en formato Markdown
async def tool_redactor(news: list) -> list:
    log_techAI.info("Redactando las noticias...")
    sys = (
        "Eres un redactor profesional que escribe resúmenes de noticias tecnológicas."
        "Utiliza un tono directo y profesional, pero cercano."
        "No incluyas ni fechas ni urls en el resumen."
        "Al final del resumen, incluye una línea horizontal `---` e invita a visitar la pagina de la noticia."
        "Devuelve el resultado en formato Markdown."
        "Usa la fuente y la URL de la noticia para proporcionar contexto."
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
            response = await _response(build_kwargs(config="search", system=sys, user=user))
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


# ---------- PIPELINES ----------
class Pipeline(Enum):
    TEST = auto()  # Para pruebas
    POST = auto()  # Para generar posts
    NEWS = auto()  # Para obtener noticias


async def run_pipeline(data: dict, mode: Pipeline) -> str:
    log_techAI.info("Ejecutando el pipeline en modo: %s", mode.name)

    if mode is Pipeline.TEST:
        log_techAI.info("Modo de prueba activado.")
        return "Pipeline de prueba ejecutado correctamente."

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


# ---------- GENERATE POST ----------
async def gen_post(data: dict, mode: Pipeline) -> str:
    log_techAI.info("Generando post...")

    try:
        data = data if isinstance(data, dict) else json.loads(data)
        response = await run_pipeline(data, mode)
        log_techAI.info("Post generado con éxito.")
        return response

    except Exception as e:
        log_techAI.error("Error generando el post: %s", e)
        raise


# ---------- GET NEWS ----------
async def get_news(mode: Pipeline) -> list:
    try:
        response = await run_pipeline(None, mode)
        log_techAI.info(response)
        return response

    except Exception as e:
        log_techAI.error("Error obteniendo noticias: %s", e)
        raise