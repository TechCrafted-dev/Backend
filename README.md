## TechCrafted API

[![Python](https://img.shields.io/badge/-Python-3776AB?style=flat&logo=python&logoColor=fff)](#tecnologías)
[![SQLite](https://img.shields.io/badge/-SQLite-003B57?style=flat&logo=sqlite&logoColor=white)](#tecnologías)
[![GitHub](https://img.shields.io/badge/-GitHub-181717?style=flat&logo=github&logoColor=white)](#tecnologías)
[![OpenAI](https://img.shields.io/badge/-OpenAI-412991?style=flat&logo=openai&logoColor=white)](#tecnologías)

¡Bienvenido a **TechCrafted API**, la plataforma que automatiza la recopilación de métricas de GitHub y la generación de contenido técnico listo para publicar!  
El servicio expone una API REST construida con FastAPI y respaldada por SQLAlchemy, de modo que puedas consultar, almacenar y enriquecer datos de repositorios, así como generar artículos con tecnología de IA de forma sencilla y escalable.

---

### 🏆 Puntos fuertes

| Funcionalidad | Descripción |
| ------------- | ----------- |
| **Extracción inteligente de datos** | Consume la API de GitHub y persiste estadísticas de tráfico, estrellas, forks, watchers y más. |
| **Generación de artículos con IA** | Combina OpenAI y plantillas internas para crear entradas de blog optimizadas en Markdown. |
| **Pipeline asíncrono y desacoplado** | Tareas de larga duración se ejecutan de manera no bloqueante, garantizando alto rendimiento. |
| **Observabilidad total** | Logging granular y hooks SQL para medir y trazar cada consulta. |
| **Listo para producción** | Imagen Docker ligera, orquestación con Jenkins y health-checks incorporados. |

---

### 🚀 Casos de uso

1. **Desarrolladores** que deseen integrar métricas de sus repositorios en dashboards personalizados.  
2. **Equipos de marketing técnico** que necesiten contenido actualizado y basado en datos reales.  
3. **Start-ups** que quieran automatizar informes de rendimiento de proyectos open-source.  
4. **Blogs y comunidades** que busquen aumentar la cadencia de publicación con artículos generados por IA.

---

### 🏗️ Arquitectura en un vistazo

```
                   ┌────────┐      ┌───────────┐      ┌──────────┐
 [GitHub API] ───► │ github │ ───► │  FastAPI  │ ───► │ database │ ───► [SQLITE]
                   └────────┘      └───────────┘      └──────────┘
                                        ▲
                                        │
                               ┌─────────────────┐
             [OpenAI]  ──────► │ techAI Pipeline │
                               └─────────────────┘
```


---

### 📋 Requisitos

- Python ≥ 3.11  
- `virtualenv`  
- Docker ≥ 24 (opcional, recomendado para despliegues)  
- Claves de acceso a GitHub y OpenAI (variables de entorno)

---

### ⚙️ Instalación rápida

```shell script
# 1. Clona el repositorio
$ git clone https://github.com/TechCrafted-dev/Backend.git
$ cd techcrafted-api

# 2. Crea y activa un entorno virtual
$ python -m venv .venv
$ source .venv/bin/activate

# 3. Instala dependencias
$ pip install -r requirements.txt

# 4. Copia la plantilla de configuración
$ cp config_template.py config.py
# → Rellena las variables sensibles (tokens, API keys, etc.)

# 5. Inicia la API
$ uvicorn main:app --reload
```


### 🐳 Despliegue con Docker

```shell script
$ docker build -t techcrafted-api:latest .
$ mkdir -p ${HOME}/techcrafted-api/data
$ docker run -d -p 3000:3000 \
    --restart unless-stopped \
    -v ${HOME}/techcrafted-api/data:/app/data \
    techcrafted-api:latest
```


---

### 🧩 Principales endpoints

| Método | Ruta            | Descripción                              |
| ------ |-----------------| ---------------------------------------- |
| GET    | `/health`       | Comprobación de estado de la aplicación. |
| GET    | `/repos`        | Lista los repositorios almacenados.      |
| POST   | `/repos/update` | Fuerza la actualización de métricas.     |
| GET    | `/posts`        | Devuelve los artículos generados.        |
| POST   | `/posts`        | Ejecuta la pipeline de IA y crea un post |

Descubre el resto en el [SWAGGER](http://localhost:3000/docs) una vez que la API esté corriendo.

---

### 🔄 Flujo de generación de contenido

1. Obtén los repositorios de GitHub `POST /repos`.
2. Se actualiza la base de datos con los datos más recientes.
2. Se invoca `POST /posts`.
3. Se arma un esquema del artículo (outline) de forma dinámica.  
4. OpenAI produce un borrador extenso.  
5. Se pule el Markdown y se guarda en la base de datos.  
6. El endpoint responde con el URL o ID del nuevo post.

---

### 📅 Roadmap

- [ ] Compatibilidad con **GitLab** y **Bitbucket**.  
- [ ] Sistema de cache con Redis.  
- [ ] Plugin para publicar directamente en plataformas de blogging.  
- [ ] Panel web con visualización de métricas.

---

### 🤝 Cómo contribuir

1. Haz un fork y crea tu rama: `git checkout -b feature/mi-mejora`  
2. Sigue la guía de estilo **PEP 8** y añade pruebas si procede.  
3. Envía un _pull request_ describiendo claramente el cambio.  
4. ¡Disfruta del open-source!

---

### 📝 Licencia

Distribuido bajo la licencia **GPL 3.0**. Consulta el archivo `LICENSE` para más información.

---

¿Dudas o sugerencias? Abre un _issue_ o contacta al mantenedor principal.  
¡Gracias por interesarte en **TechCrafted API**!