#!/usr/bin/env python3
"""
Servidor MCP de WordPress en Python
Servidor MCP que expone funcionalidades de WordPress usando Basic Auth
Incluye generación de contenido con IA usando Claude (Anthropic)
"""

import asyncio
import json
import sys
import os
import logging
from typing import Any, Dict, List, Optional
import httpx
from base64 import b64encode

# Importar el SDK de MCP
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Importar el generador de contenido con IA
try:
    from .ai_content_generator import AIContentGenerator
except ImportError:
    from ai_content_generator import AIContentGenerator

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WordPressAPI:
    """Cliente para interactuar con el REST API de WordPress"""

    def __init__(self, url: str, username: str, password: str):
        self.url = url.rstrip('/')
        self.username = username
        self.password = password

        # Crear token de Basic Auth
        credentials = f"{username}:{password}"
        token = b64encode(credentials.encode()).decode('ascii')

        self.headers = {
            'Authorization': f'Basic {token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

    async def _request(self, method: str, endpoint: str, data: Optional[Dict] = None, params: Optional[Dict] = None) -> Any:
        """Realiza petición HTTP al API de WordPress"""
        url = f"{self.url}/wp-json{endpoint}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                if method == 'GET':
                    response = await client.get(url, headers=self.headers, params=params)
                elif method == 'POST':
                    response = await client.post(url, headers=self.headers, json=data)
                elif method == 'PUT':
                    response = await client.put(url, headers=self.headers, json=data)
                elif method == 'DELETE':
                    response = await client.delete(url, headers=self.headers)

                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                raise Exception(f"Error HTTP: {str(e)}")

    # === Categorías ===
    async def list_categories(self, per_page: int = 100) -> List[Dict]:
        """Lista todas las categorías"""
        return await self._request('GET', '/wp/v2/categories', params={'per_page': per_page})

    # === Posts ===
    async def list_posts(self, per_page: int = 10, page: int = 1, status: str = 'any') -> List[Dict]:
        """Lista posts"""
        params = {'per_page': per_page, 'page': page, 'status': status}
        return await self._request('GET', '/wp/v2/posts', params=params)

    async def search_posts(self, search: str, per_page: int = 10) -> List[Dict]:
        """Busca posts por término"""
        params = {'search': search, 'per_page': per_page}
        return await self._request('GET', '/wp/v2/posts', params=params)

    async def create_post(self, title: str, content: str, status: str = 'draft',
                         categories: Optional[List[int]] = None,
                         tags: Optional[List[int]] = None) -> Dict:
        """Crea un nuevo post"""
        data = {
            'title': title,
            'content': content,
            'status': status
        }
        if categories:
            data['categories'] = categories
        if tags:
            data['tags'] = tags

        return await self._request('POST', '/wp/v2/posts', data=data)

    async def update_post(self, post_id: int, **kwargs) -> Dict:
        """Actualiza un post existente"""
        return await self._request('PUT', f'/wp/v2/posts/{post_id}', data=kwargs)

    async def delete_post(self, post_id: int, force: bool = False) -> Dict:
        """Elimina un post"""
        params = {'force': 'true' if force else 'false'}
        return await self._request('DELETE', f'/wp/v2/posts/{post_id}', params=params)

    # === Media ===
    async def upload_media(self, file_path: str, title: Optional[str] = None,
                          alt_text: Optional[str] = None) -> Dict:
        """Sube un archivo multimedia"""
        file_name = os.path.basename(file_path)

        # Leer archivo
        with open(file_path, 'rb') as f:
            file_data = f.read()

        # Headers especiales para subida de archivos
        headers = {
            'Authorization': self.headers['Authorization'],
            'Content-Disposition': f'attachment; filename="{file_name}"',
        }

        # Detectar tipo MIME
        import mimetypes
        content_type, _ = mimetypes.guess_type(file_path)
        if content_type:
            headers['Content-Type'] = content_type

        url = f"{self.url}/wp-json/wp/v2/media"

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, headers=headers, content=file_data)
            response.raise_for_status()
            media = response.json()

        # Actualizar título y alt text si se proporcionan
        if title or alt_text:
            update_data = {}
            if title:
                update_data['title'] = title
            if alt_text:
                update_data['alt_text'] = alt_text

            media = await self._request('PUT', f'/wp/v2/media/{media["id"]}', data=update_data)

        return media

    # === Tags ===
    async def list_tags(self, per_page: int = 100) -> List[Dict]:
        """Lista todas las etiquetas"""
        return await self._request('GET', '/wp/v2/tags', params={'per_page': per_page})

    async def search_tags(self, search: str, per_page: int = 10) -> List[Dict]:
        """Busca etiquetas por término"""
        params = {'search': search, 'per_page': per_page}
        return await self._request('GET', '/wp/v2/tags', params=params)

    async def create_tag(self, name: str, description: Optional[str] = None,
                        slug: Optional[str] = None) -> Dict:
        """Crea una nueva etiqueta"""
        data = {'name': name}
        if description:
            data['description'] = description
        if slug:
            data['slug'] = slug

        return await self._request('POST', '/wp/v2/tags', data=data)


class WordPressMCPServer:
    """Servidor MCP para WordPress con IA integrada"""

    def __init__(self):
        self.server = Server("wordpress-mcp-python")
        self.wp: Optional[WordPressAPI] = None
        self.ai_generator: Optional[AIContentGenerator] = None

        # Inicializar generador de IA
        try:
            self.ai_generator = AIContentGenerator()
            if self.ai_generator.is_available():
                logger.info("✅ Generador de IA inicializado correctamente")
            else:
                logger.warning("⚠️ Generador de IA no disponible (falta ANTHROPIC_API_KEY)")
        except Exception as e:
            logger.error(f"❌ Error inicializando generador de IA: {e}")
            self.ai_generator = None

        # Registrar handlers
        self.setup_handlers()

    def setup_handlers(self):
        """Configura los handlers del servidor MCP"""

        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            """Lista todas las herramientas disponibles"""
            return [
                Tool(
                    name="list_categories",
                    description="Lista todas las categorías disponibles en WordPress",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "per_page": {
                                "type": "integer",
                                "description": "Número de categorías a obtener (default: 100)",
                                "default": 100
                            }
                        }
                    }
                ),
                Tool(
                    name="list_posts",
                    description="Lista posts de WordPress con paginación",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "per_page": {
                                "type": "integer",
                                "description": "Posts por página (default: 10)",
                                "default": 10
                            },
                            "page": {
                                "type": "integer",
                                "description": "Número de página (default: 1)",
                                "default": 1
                            },
                            "status": {
                                "type": "string",
                                "description": "Estado del post: publish, draft, pending, any (default: any)",
                                "default": "any"
                            }
                        }
                    }
                ),
                Tool(
                    name="search_posts",
                    description="Busca posts por término de búsqueda",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "search": {
                                "type": "string",
                                "description": "Término de búsqueda"
                            },
                            "per_page": {
                                "type": "integer",
                                "description": "Número de resultados (default: 10)",
                                "default": 10
                            }
                        },
                        "required": ["search"]
                    }
                ),
                Tool(
                    name="create_post",
                    description="Crea un nuevo post en WordPress",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "title": {
                                "type": "string",
                                "description": "Título del post"
                            },
                            "content": {
                                "type": "string",
                                "description": "Contenido del post (HTML permitido)"
                            },
                            "status": {
                                "type": "string",
                                "description": "Estado: draft, publish, pending (default: draft)",
                                "default": "draft"
                            },
                            "categories": {
                                "type": "array",
                                "items": {"type": "integer"},
                                "description": "IDs de categorías"
                            },
                            "tags": {
                                "type": "array",
                                "items": {"type": "integer"},
                                "description": "IDs de etiquetas"
                            }
                        },
                        "required": ["title", "content"]
                    }
                ),
                Tool(
                    name="update_post",
                    description="Actualiza un post existente",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "post_id": {
                                "type": "integer",
                                "description": "ID del post a actualizar"
                            },
                            "title": {
                                "type": "string",
                                "description": "Nuevo título"
                            },
                            "content": {
                                "type": "string",
                                "description": "Nuevo contenido"
                            },
                            "status": {
                                "type": "string",
                                "description": "Nuevo estado"
                            },
                            "categories": {
                                "type": "array",
                                "items": {"type": "integer"},
                                "description": "IDs de categorías"
                            },
                            "tags": {
                                "type": "array",
                                "items": {"type": "integer"},
                                "description": "IDs de etiquetas"
                            }
                        },
                        "required": ["post_id"]
                    }
                ),
                Tool(
                    name="delete_post",
                    description="Elimina un post (mueve a papelera o elimina permanentemente)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "post_id": {
                                "type": "integer",
                                "description": "ID del post a eliminar"
                            },
                            "force": {
                                "type": "boolean",
                                "description": "true = eliminar permanentemente, false = mover a papelera (default: false)",
                                "default": False
                            }
                        },
                        "required": ["post_id"]
                    }
                ),
                Tool(
                    name="upload_media",
                    description="Sube un archivo multimedia a WordPress",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "Ruta al archivo a subir"
                            },
                            "title": {
                                "type": "string",
                                "description": "Título del archivo"
                            },
                            "alt_text": {
                                "type": "string",
                                "description": "Texto alternativo para imágenes"
                            }
                        },
                        "required": ["file_path"]
                    }
                ),
                Tool(
                    name="list_tags",
                    description="Lista todas las etiquetas (tags) disponibles",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "per_page": {
                                "type": "integer",
                                "description": "Número de etiquetas a obtener (default: 100)",
                                "default": 100
                            }
                        }
                    }
                ),
                Tool(
                    name="search_tags",
                    description="Busca etiquetas por término",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "search": {
                                "type": "string",
                                "description": "Término de búsqueda"
                            },
                            "per_page": {
                                "type": "integer",
                                "description": "Número de resultados (default: 10)",
                                "default": 10
                            }
                        },
                        "required": ["search"]
                    }
                ),
                Tool(
                    name="create_tag",
                    description="Crea una nueva etiqueta",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "Nombre de la etiqueta"
                            },
                            "description": {
                                "type": "string",
                                "description": "Descripción de la etiqueta"
                            },
                            "slug": {
                                "type": "string",
                                "description": "Slug de la etiqueta (URL-friendly)"
                            }
                        },
                        "required": ["name"]
                    }
                ),
                # === Herramientas con IA ===
                Tool(
                    name="generate_post_with_ai",
                    description="Genera y publica un post completo usando IA (Claude). Solo necesitas un prompt describiendo el tema. La IA generará título, contenido, extracto, categorías y tags automáticamente.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "prompt": {
                                "type": "string",
                                "description": "Descripción del tema del post (ej: 'Escribe sobre las ventajas de la inteligencia artificial en medicina')"
                            },
                            "style": {
                                "type": "string",
                                "enum": ["profesional", "casual", "técnico", "creativo"],
                                "description": "Estilo de escritura (default: profesional)",
                                "default": "profesional"
                            },
                            "tone": {
                                "type": "string",
                                "enum": ["informativo", "persuasivo", "educativo", "entretenido"],
                                "description": "Tono del contenido (default: informativo)",
                                "default": "informativo"
                            },
                            "language": {
                                "type": "string",
                                "description": "Idioma del contenido (default: español)",
                                "default": "español"
                            },
                            "status": {
                                "type": "string",
                                "enum": ["draft", "publish", "pending"],
                                "description": "Estado del post (default: draft)",
                                "default": "draft"
                            }
                        },
                        "required": ["prompt"]
                    }
                ),
                Tool(
                    name="improve_post_with_ai",
                    description="Mejora un post existente usando IA. Optimiza SEO, claridad y estructura del contenido.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "post_id": {
                                "type": "integer",
                                "description": "ID del post a mejorar"
                            },
                            "improvements": {
                                "type": "string",
                                "description": "Aspectos a mejorar (ej: 'mejorar SEO y legibilidad', 'hacer más técnico', 'simplificar lenguaje')",
                                "default": "mejorar SEO, claridad y estructura"
                            }
                        },
                        "required": ["post_id"]
                    }
                ),
                Tool(
                    name="generate_content_from_prompt",
                    description="Genera contenido usando IA sin publicarlo. Útil para obtener solo el contenido generado como JSON.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "prompt": {
                                "type": "string",
                                "description": "Descripción del contenido a generar"
                            },
                            "style": {
                                "type": "string",
                                "enum": ["profesional", "casual", "técnico", "creativo"],
                                "description": "Estilo de escritura",
                                "default": "profesional"
                            },
                            "tone": {
                                "type": "string",
                                "enum": ["informativo", "persuasivo", "educativo", "entretenido"],
                                "description": "Tono del contenido",
                                "default": "informativo"
                            },
                            "language": {
                                "type": "string",
                                "description": "Idioma del contenido",
                                "default": "español"
                            }
                        },
                        "required": ["prompt"]
                    }
                ),
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict) -> List[TextContent]:
            """Ejecuta una herramienta"""

            if not self.wp:
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": "WordPress API no inicializado. Configure WP_URL, WP_USERNAME y WP_PASSWORD"})
                )]

            try:
                result = None

                if name == "list_categories":
                    result = await self.wp.list_categories(
                        per_page=arguments.get('per_page', 100)
                    )

                elif name == "list_posts":
                    result = await self.wp.list_posts(
                        per_page=arguments.get('per_page', 10),
                        page=arguments.get('page', 1),
                        status=arguments.get('status', 'any')
                    )

                elif name == "search_posts":
                    result = await self.wp.search_posts(
                        search=arguments['search'],
                        per_page=arguments.get('per_page', 10)
                    )

                elif name == "create_post":
                    result = await self.wp.create_post(
                        title=arguments['title'],
                        content=arguments['content'],
                        status=arguments.get('status', 'draft'),
                        categories=arguments.get('categories'),
                        tags=arguments.get('tags')
                    )

                elif name == "update_post":
                    post_id = arguments.pop('post_id')
                    result = await self.wp.update_post(post_id, **arguments)

                elif name == "delete_post":
                    result = await self.wp.delete_post(
                        post_id=arguments['post_id'],
                        force=arguments.get('force', False)
                    )

                elif name == "upload_media":
                    result = await self.wp.upload_media(
                        file_path=arguments['file_path'],
                        title=arguments.get('title'),
                        alt_text=arguments.get('alt_text')
                    )

                elif name == "list_tags":
                    result = await self.wp.list_tags(
                        per_page=arguments.get('per_page', 100)
                    )

                elif name == "search_tags":
                    result = await self.wp.search_tags(
                        search=arguments['search'],
                        per_page=arguments.get('per_page', 10)
                    )

                elif name == "create_tag":
                    result = await self.wp.create_tag(
                        name=arguments['name'],
                        description=arguments.get('description'),
                        slug=arguments.get('slug')
                    )

                # === Herramientas con IA ===
                elif name == "generate_post_with_ai":
                    # Verificar que el generador de IA esté disponible
                    if not self.ai_generator or not self.ai_generator.is_available():
                        return [TextContent(
                            type="text",
                            text=json.dumps({
                                "error": "Generador de IA no disponible. Configure ANTHROPIC_API_KEY en las variables de entorno."
                            })
                        )]

                    logger.info(f"🤖 Generando post con IA: {arguments['prompt'][:50]}...")

                    # Generar contenido con IA
                    ai_content = self.ai_generator.generate_post_content(
                        prompt=arguments['prompt'],
                        style=arguments.get('style', 'profesional'),
                        tone=arguments.get('tone', 'informativo'),
                        language=arguments.get('language', 'español')
                    )

                    if not ai_content:
                        return [TextContent(
                            type="text",
                            text=json.dumps({"error": "Error generando contenido con IA"})
                        )]

                    # Crear el post en WordPress
                    try:
                        # Obtener o crear categorías
                        category_ids = []
                        if ai_content.get('categories'):
                            for cat_name in ai_content['categories']:
                                # Buscar categoría existente
                                cats = await self.wp.list_categories(per_page=100)
                                found = False
                                for cat in cats:
                                    if cat.get('name', '').lower() == cat_name.lower():
                                        category_ids.append(cat['id'])
                                        found = True
                                        break

                                # Si no existe, intentar crearla
                                if not found:
                                    try:
                                        # Crear categoría (nota: esto requiere permisos adicionales)
                                        logger.info(f"📁 Usando categoría generada: {cat_name}")
                                    except:
                                        pass

                        # Obtener o crear tags
                        tag_ids = []
                        if ai_content.get('tags'):
                            for tag_name in ai_content['tags']:
                                # Buscar tag existente
                                tags = await self.wp.list_tags(per_page=100)
                                found = False
                                for tag in tags:
                                    if tag.get('name', '').lower() == tag_name.lower():
                                        tag_ids.append(tag['id'])
                                        found = True
                                        break

                                # Si no existe, intentar crearlo
                                if not found:
                                    try:
                                        new_tag = await self.wp.create_tag(name=tag_name)
                                        tag_ids.append(new_tag['id'])
                                    except:
                                        pass

                        # Crear post
                        post_result = await self.wp.create_post(
                            title=ai_content['title'],
                            content=ai_content['content'],
                            status=arguments.get('status', 'draft'),
                            categories=category_ids if category_ids else None,
                            tags=tag_ids if tag_ids else None
                        )

                        # Añadir información de la IA a la respuesta
                        post_result['ai_generated'] = True
                        post_result['ai_categories'] = ai_content.get('categories', [])
                        post_result['ai_tags'] = ai_content.get('tags', [])
                        post_result['excerpt'] = ai_content.get('excerpt', '')

                        result = post_result

                    except Exception as e:
                        logger.error(f"❌ Error creando post: {e}")
                        return [TextContent(
                            type="text",
                            text=json.dumps({
                                "error": f"Error creando post en WordPress: {str(e)}",
                                "ai_content": ai_content
                            })
                        )]

                elif name == "improve_post_with_ai":
                    # Verificar que el generador de IA esté disponible
                    if not self.ai_generator or not self.ai_generator.is_available():
                        return [TextContent(
                            type="text",
                            text=json.dumps({
                                "error": "Generador de IA no disponible. Configure ANTHROPIC_API_KEY en las variables de entorno."
                            })
                        )]

                    post_id = arguments['post_id']
                    logger.info(f"🔧 Mejorando post {post_id} con IA...")

                    # Obtener el post actual
                    try:
                        posts = await self.wp.list_posts(per_page=1, page=1)
                        current_post = None

                        # Buscar el post por ID (simplificado - en producción usar endpoint específico)
                        for post in posts:
                            if post.get('id') == post_id:
                                current_post = post
                                break

                        if not current_post:
                            return [TextContent(
                                type="text",
                                text=json.dumps({"error": f"Post {post_id} no encontrado"})
                            )]

                        # Obtener contenido actual
                        current_content = current_post.get('content', {}).get('rendered', '')

                        # Mejorar con IA
                        improved_content = self.ai_generator.improve_content(
                            original_content=current_content,
                            improvements=arguments.get('improvements', 'mejorar SEO, claridad y estructura')
                        )

                        if not improved_content:
                            return [TextContent(
                                type="text",
                                text=json.dumps({"error": "Error mejorando contenido con IA"})
                            )]

                        # Actualizar post
                        result = await self.wp.update_post(
                            post_id=post_id,
                            content=improved_content
                        )

                        result['ai_improved'] = True

                    except Exception as e:
                        logger.error(f"❌ Error mejorando post: {e}")
                        return [TextContent(
                            type="text",
                            text=json.dumps({"error": f"Error mejorando post: {str(e)}"})
                        )]

                elif name == "generate_content_from_prompt":
                    # Verificar que el generador de IA esté disponible
                    if not self.ai_generator or not self.ai_generator.is_available():
                        return [TextContent(
                            type="text",
                            text=json.dumps({
                                "error": "Generador de IA no disponible. Configure ANTHROPIC_API_KEY en las variables de entorno."
                            })
                        )]

                    logger.info(f"🤖 Generando contenido con IA: {arguments['prompt'][:50]}...")

                    # Generar contenido con IA
                    ai_content = self.ai_generator.generate_post_content(
                        prompt=arguments['prompt'],
                        style=arguments.get('style', 'profesional'),
                        tone=arguments.get('tone', 'informativo'),
                        language=arguments.get('language', 'español')
                    )

                    if not ai_content:
                        return [TextContent(
                            type="text",
                            text=json.dumps({"error": "Error generando contenido con IA"})
                        )]

                    result = {
                        "success": True,
                        "ai_generated": True,
                        "content": ai_content
                    }

                else:
                    return [TextContent(
                        type="text",
                        text=json.dumps({"error": f"Herramienta desconocida: {name}"})
                    )]

                return [TextContent(
                    type="text",
                    text=json.dumps(result, indent=2, ensure_ascii=False)
                )]

            except Exception as e:
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": str(e)})
                )]

    async def run(self):
        """Inicia el servidor MCP"""

        # Obtener credenciales de variables de entorno
        wp_url = os.getenv('WP_URL')
        wp_username = os.getenv('WP_USER')
        wp_password = os.getenv('WP_APP_PASSWORD')

         print("WP_URL =", wp_url)
         print("WP_USER =", wp_username)
         print("WP_APP_PASSWORD =", "SET" if wp_password else "MISSING")
        
        if not all([wp_url, wp_username, wp_password]):
            print("ERROR: Debes configurar WP_URL, WP_USERNAME y WP_PASSWORD", file=sys.stderr)
            sys.exit(1)

        # Inicializar cliente de WordPress
        self.wp = WordPressAPI(wp_url, wp_username, wp_password)

        # Iniciar servidor STDIO
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


async def main():
    """Punto de entrada principal"""
    server = WordPressMCPServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
