#!/usr/bin/env python3
"""
HTTP Wrapper para el servidor MCP
Expone el servidor MCP sobre HTTP usando SSE (Server-Sent Events)
Compatible con n8n Cloud y otros clientes HTTP
"""

import asyncio
import json
import logging
from typing import Optional
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Importar el servidor MCP
from .server import WordPressMCPServer

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Crear aplicación FastAPI
app = FastAPI(
    title="WordPress MCP Server (HTTP/SSE)",
    description="Servidor MCP de WordPress expuesto sobre HTTP para n8n Cloud",
    version="3.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Instancia global del servidor MCP
mcp_server: Optional[WordPressMCPServer] = None


@app.on_event("startup")
async def startup():
    """Inicializa el servidor MCP"""
    global mcp_server

    # Verificar credenciales (usar WP_USER y WP_APP_PASSWORD para compatibilidad con Render)
    wp_url = os.getenv('WP_URL')
    wp_username = os.getenv('WP_USER') or os.getenv('WP_USERNAME')
    wp_password = os.getenv('WP_APP_PASSWORD') or os.getenv('WP_PASSWORD')

    logger.info(f"WP_URL={bool(wp_url)} WP_USER={bool(wp_username)} WP_APP_PASSWORD={bool(wp_password)}")

    if not all([wp_url, wp_username, wp_password]):
        raise RuntimeError("Faltan credenciales de WordPress. Configure WP_URL, WP_USER y WP_APP_PASSWORD")

    # Configurar variables de entorno para el servidor MCP
    os.environ['WP_USER'] = wp_username
    os.environ['WP_APP_PASSWORD'] = wp_password

    # Inicializar servidor MCP
    mcp_server = WordPressMCPServer()
    logger.info(f"WordPress MCP Server inicializado: {wp_url}")


@app.get("/")
@app.head("/")
async def root_get(request: Request):
    """Info del servidor (solo para GET/HEAD)"""
    return {
        "name": "WordPress MCP Server",
        "version": "3.0.0",
        "protocol": "MCP over HTTP Streamable",
        "wordpress_url": os.getenv('WP_URL'),
        "ai_available": mcp_server.ai_generator.is_available() if mcp_server and mcp_server.ai_generator else False,
        "endpoints": {
            "root": "/ (POST)",
            "stream": "/stream (POST)",
            "mcp": "/mcp (POST)",
            "messages": "/mcp/messages (POST)"
        }
    }


@app.get("/health")
@app.head("/health")
async def health():
    """Health check"""
    return {"status": "healthy"}


@app.get("/mcp/sse")
async def mcp_sse_endpoint(request: Request):
    """
    Endpoint SSE para comunicación MCP
    Este es el endpoint que usarás en n8n Cloud
    """
    async def event_generator():
        """Genera eventos SSE"""
        try:
            # Enviar mensaje de inicialización
            init_message = {
                "jsonrpc": "2.0",
                "method": "initialized",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "wordpress-mcp-python",
                        "version": "3.0.0"
                    }
                }
            }
            yield f"data: {json.dumps(init_message)}\n\n"

            # Mantener conexión abierta
            while True:
                if await request.is_disconnected():
                    break
                await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"Error en SSE: {e}")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.post("/")
@app.post("/stream")
@app.post("/mcp")
@app.post("/mcp/messages")
async def mcp_messages_endpoint(request: Request):
    """
    Endpoint para enviar mensajes MCP (llamadas a tools)
    n8n enviará las llamadas aquí
    Compatible con múltiples rutas: /stream, /mcp, /mcp/messages
    """
    try:
        # Parsear request JSON-RPC
        body = await request.json()
        logger.info(f"Mensaje MCP recibido: {body.get('method')}")

        # Manejar diferentes métodos
        method = body.get("method")
        params = body.get("params", {})

        if method == "initialize":
            # Respuesta de inicialización
            return {
                "jsonrpc": "2.0",
                "id": body.get("id"),
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "wordpress-mcp-python",
                        "version": "3.0.0"
                    }
                }
            }

        elif method == "tools/list":
            # Obtener lista de herramientas directamente del servidor MCP
            # En lugar de acceder a internos, usamos el handler registrado
            from mcp.types import Tool

            # Lista COMPLETA de tools (copiada de server.py)
            tools = [
                {
                    "name": "list_categories",
                    "description": "Lista todas las categorías disponibles en WordPress",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "per_page": {"type": "integer", "description": "Número de categorías a obtener (default: 100)", "default": 100}
                        }
                    }
                },
                {
                    "name": "list_posts",
                    "description": "Lista posts de WordPress con paginación",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "per_page": {"type": "integer", "description": "Posts por página (default: 10)", "default": 10},
                            "page": {"type": "integer", "description": "Número de página (default: 1)", "default": 1},
                            "status": {"type": "string", "description": "Estado del post: publish, draft, pending, any (default: any)", "default": "any"}
                        }
                    }
                },
                {
                    "name": "search_posts",
                    "description": "Busca posts por término de búsqueda",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "search": {"type": "string", "description": "Término de búsqueda"},
                            "per_page": {"type": "integer", "description": "Número de resultados (default: 10)", "default": 10}
                        },
                        "required": ["search"]
                    }
                },
                {
                    "name": "create_post",
                    "description": "Crea un nuevo post en WordPress",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "Título del post"},
                            "content": {"type": "string", "description": "Contenido del post (HTML permitido)"},
                            "status": {"type": "string", "description": "Estado: draft, publish, pending (default: draft)", "default": "draft"},
                            "categories": {"type": "array", "items": {"type": "integer"}, "description": "IDs de categorías"},
                            "tags": {"type": "array", "items": {"type": "integer"}, "description": "IDs de etiquetas"}
                        },
                        "required": ["title", "content"]
                    }
                },
                {
                    "name": "update_post",
                    "description": "Actualiza un post existente",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "post_id": {"type": "integer", "description": "ID del post a actualizar"},
                            "title": {"type": "string", "description": "Nuevo título"},
                            "content": {"type": "string", "description": "Nuevo contenido"},
                            "status": {"type": "string", "description": "Nuevo estado"},
                            "categories": {"type": "array", "items": {"type": "integer"}, "description": "IDs de categorías"},
                            "tags": {"type": "array", "items": {"type": "integer"}, "description": "IDs de etiquetas"}
                        },
                        "required": ["post_id"]
                    }
                },
                {
                    "name": "delete_post",
                    "description": "Elimina un post (mueve a papelera o elimina permanentemente)",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "post_id": {"type": "integer", "description": "ID del post a eliminar"},
                            "force": {"type": "boolean", "description": "true = eliminar permanentemente, false = mover a papelera (default: false)", "default": False}
                        },
                        "required": ["post_id"]
                    }
                },
                {
                    "name": "upload_media",
                    "description": "Sube un archivo multimedia a WordPress",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "file_path": {"type": "string", "description": "Ruta al archivo a subir"},
                            "title": {"type": "string", "description": "Título del archivo"},
                            "alt_text": {"type": "string", "description": "Texto alternativo para imágenes"}
                        },
                        "required": ["file_path"]
                    }
                },
                {
                    "name": "list_tags",
                    "description": "Lista todas las etiquetas (tags) disponibles",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "per_page": {"type": "integer", "description": "Número de etiquetas a obtener (default: 100)", "default": 100}
                        }
                    }
                },
                {
                    "name": "search_tags",
                    "description": "Busca etiquetas por término",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "search": {"type": "string", "description": "Término de búsqueda"},
                            "per_page": {"type": "integer", "description": "Número de resultados (default: 10)", "default": 10}
                        },
                        "required": ["search"]
                    }
                },
                {
                    "name": "create_tag",
                    "description": "Crea una nueva etiqueta",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Nombre de la etiqueta"},
                            "description": {"type": "string", "description": "Descripción de la etiqueta"},
                            "slug": {"type": "string", "description": "Slug de la etiqueta (URL-friendly)"}
                        },
                        "required": ["name"]
                    }
                },
                {
                    "name": "generate_post_with_ai",
                    "description": "Genera y publica un post completo usando IA (Groq). Solo necesitas un prompt describiendo el tema.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "prompt": {"type": "string", "description": "Descripción del tema del post"},
                            "style": {"type": "string", "enum": ["profesional", "casual", "técnico", "creativo"], "default": "profesional"},
                            "tone": {"type": "string", "enum": ["informativo", "persuasivo", "educativo", "entretenido"], "default": "informativo"},
                            "language": {"type": "string", "description": "Idioma del contenido (default: español)", "default": "español"},
                            "status": {"type": "string", "enum": ["draft", "publish", "pending"], "default": "draft"}
                        },
                        "required": ["prompt"]
                    }
                }
            ]

            return {
                "jsonrpc": "2.0",
                "id": body.get("id"),
                "result": {
                    "tools": tools
                }
            }

        elif method == "tools/call":
            # Ejecutar herramienta usando la lógica del servidor WordPress
            tool_name = params.get("name")
            arguments = params.get("arguments", {})

            logger.info(f"Ejecutando tool: {tool_name} con argumentos: {arguments}")

            # Importar WordPressAPI y AIContentGenerator
            from .server import WordPressAPI
            from .ai_content_generator import AIContentGenerator

            # Inicializar cliente WP
            wp_url = os.getenv('WP_URL')
            wp_username = os.getenv('WP_USER')
            wp_password = os.getenv('WP_APP_PASSWORD')

            wp = WordPressAPI(wp_url, wp_username, wp_password)

            # Ejecutar la herramienta
            result = None

            if tool_name == "list_categories":
                result = await wp.list_categories(per_page=arguments.get("per_page", 100))

            elif tool_name == "list_posts":
                result = await wp.list_posts(
                    per_page=arguments.get("per_page", 10),
                    page=arguments.get("page", 1),
                    status=arguments.get("status", "any")
                )

            elif tool_name == "search_posts":
                result = await wp.search_posts(
                    search=arguments["search"],
                    per_page=arguments.get("per_page", 10)
                )

            elif tool_name == "create_post":
                result = await wp.create_post(
                    title=arguments["title"],
                    content=arguments["content"],
                    status=arguments.get("status", "draft"),
                    categories=arguments.get("categories"),
                    tags=arguments.get("tags")
                )

            elif tool_name == "update_post":
                result = await wp.update_post(
                    post_id=arguments["post_id"],
                    title=arguments.get("title"),
                    content=arguments.get("content"),
                    status=arguments.get("status"),
                    categories=arguments.get("categories"),
                    tags=arguments.get("tags")
                )

            elif tool_name == "delete_post":
                result = await wp.delete_post(
                    post_id=arguments["post_id"],
                    force=arguments.get("force", False)
                )

            elif tool_name == "upload_media":
                result = await wp.upload_media(
                    file_path=arguments["file_path"],
                    title=arguments.get("title"),
                    alt_text=arguments.get("alt_text")
                )

            elif tool_name == "list_tags":
                result = await wp.list_tags(per_page=arguments.get("per_page", 100))

            elif tool_name == "search_tags":
                result = await wp.search_tags(
                    search=arguments["search"],
                    per_page=arguments.get("per_page", 10)
                )

            elif tool_name == "create_tag":
                result = await wp.create_tag(
                    name=arguments["name"],
                    description=arguments.get("description"),
                    slug=arguments.get("slug")
                )

            elif tool_name == "generate_post_with_ai":
                # NUEVO: Usar Groq para generar contenido directamente
                ai_gen = AIContentGenerator()
                if not ai_gen.is_available():
                    raise Exception("Generador de IA no disponible.")

                logger.info(f"Generando post con IA: {arguments['prompt'][:50]}...")

                ai_content = ai_gen.generate_post_content(
                    prompt=arguments["prompt"],
                    style=arguments.get("style", "profesional"),
                    tone=arguments.get("tone", "informativo"),
                    language=arguments.get("language", "español")
                )

                if not ai_content:
                    raise Exception("Error generando contenido con IA.")

                # Obtener o crear categorías
                category_ids = []
                if ai_content.get("categories"):
                    for cat_name in ai_content["categories"]:
                        # Buscar categoría existente
                        cats = await wp.list_categories(per_page=100)
                        found = False
                        for cat in cats:
                            if cat.get("name", "").lower() == cat_name.lower():
                                category_ids.append(cat["id"])
                                found = True
                                logger.info(f"Categoría encontrada: {cat_name} (ID: {cat['id']})")
                                break

                        # Si no existe, intentar crearla
                        if not found:
                            try:
                                # Crear categoría (nota: esto requiere permisos adicionales)
                                logger.info(f"Usando categoría generada: {cat_name}")
                            except:
                                pass

                # Obtener o crear tags
                tag_ids = []
                if ai_content.get("tags"):
                    for tag_name in ai_content["tags"]:
                        # Buscar tag existente
                        tags = await wp.list_tags(per_page=100)
                        found = False
                        for tag in tags:
                            if tag.get("name", "").lower() == tag_name.lower():
                                tag_ids.append(tag["id"])
                                found = True
                                logger.info(f"Tag encontrado: {tag_name} (ID: {tag['id']})")
                                break

                        # Si no existe, intentar crearlo
                        if not found:
                            try:
                                new_tag = await wp.create_tag(name=tag_name)
                                tag_ids.append(new_tag["id"])
                                logger.info(f"Tag creado: {tag_name} (ID: {new_tag['id']})")
                            except Exception as e:
                                logger.error(f"Error creando tag {tag_name}: {e}")
                                pass

                logger.info(f"IDs de categorías finales: {category_ids}")
                logger.info(f"IDs de tags finales: {tag_ids}")

                # Crear post con categorías y tags
                result = await wp.create_post(
                    title=ai_content["title"],
                    content=ai_content["content"],
                    status=arguments.get("status", "draft"),
                    categories=category_ids if category_ids else None,
                    tags=tag_ids if tag_ids else None
                )
                result["ai_generated"] = True
                result["source"] = "Groq"
                result["ai_categories"] = ai_content.get("categories", [])
                result["ai_tags"] = ai_content.get("tags", [])
                result["excerpt"] = ai_content.get("excerpt", "")

            else:
                raise Exception(f"Herramienta desconocida: {tool_name}")

            import json
            return {
                "jsonrpc": "2.0",
                "id": body.get("id"),
                "result": {
                    "content": [{"type": "text", "text": json.dumps(result, indent=2, ensure_ascii=False)}]
                }
            }

        else:
            return {
                "jsonrpc": "2.0",
                "id": body.get("id"),
                "error": {
                    "code": -32601,
                    "message": f"Método no soportado: {method}"
                }
            }

    except Exception as e:
        logger.error(f"Error procesando mensaje MCP: {e}", exc_info=True)
        return {
            "jsonrpc": "2.0",
            "id": body.get("id", None),
            "error": {
                "code": -32603,
                "message": str(e)
            }
        }


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv('PORT', 8000))

    print("=" * 60)
    print("WordPress MCP Server (HTTP/SSE)")
    print("=" * 60)
    print(f"Puerto: {port}")
    print(f"WordPress: {os.getenv('WP_URL')}")
    print(f"IA disponible: Groq")
    print()
    print("Endpoints para n8n:")
    print(f"  Endpoint: http://localhost:{port}/mcp/sse")
    print(f"  Transport: HTTP Streamable")
    print()
    print("=" * 60)
    print()

    uvicorn.run(app, host="0.0.0.0", port=port)
