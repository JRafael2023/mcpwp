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
    logger.info(f"✅ WordPress MCP Server inicializado: {wp_url}")


@app.get("/")
@app.head("/")
async def root():
    """Info del servidor"""
    return {
        "name": "WordPress MCP Server",
        "version": "3.0.0",
        "protocol": "MCP over HTTP/SSE",
        "wordpress_url": os.getenv('WP_URL'),
        "ai_available": mcp_server.ai_generator.is_available() if mcp_server and mcp_server.ai_generator else False,
        "endpoints": {
            "sse": "/mcp/sse",
            "messages": "/mcp/messages"
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


@app.post("/mcp/messages")
async def mcp_messages_endpoint(request: Request):
    """
    Endpoint para enviar mensajes MCP (llamadas a tools)
    n8n enviará las llamadas aquí
    """
    try:
        # Parsear request JSON-RPC
        body = await request.json()
        logger.info(f"📨 Mensaje MCP recibido: {body.get('method')}")

        # Manejar diferentes métodos
        method = body.get("method")
        params = body.get("params", {})

        if method == "tools/list":
            # Listar herramientas disponibles
            tools = await mcp_server.server._tool_manager.list_tools()

            return {
                "jsonrpc": "2.0",
                "id": body.get("id"),
                "result": {
                    "tools": [tool.dict() for tool in tools]
                }
            }

        elif method == "tools/call":
            # Ejecutar herramienta
            tool_name = params.get("name")
            arguments = params.get("arguments", {})

            logger.info(f"🔧 Ejecutando tool: {tool_name}")

            # Llamar a la herramienta
            result = await mcp_server.server._tool_manager.call_tool(
                name=tool_name,
                arguments=arguments
            )

            return {
                "jsonrpc": "2.0",
                "id": body.get("id"),
                "result": {
                    "content": [{"type": "text", "text": result}]
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
        logger.error(f"❌ Error procesando mensaje MCP: {e}")
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
    print("🚀 WordPress MCP Server (HTTP/SSE)")
    print("=" * 60)
    print(f"Puerto: {port}")
    print(f"WordPress: {os.getenv('WP_URL')}")
    print(f"IA disponible: {bool(os.getenv('ANTHROPIC_API_KEY'))}")
    print()
    print("Endpoints para n8n:")
    print(f"  Endpoint: http://localhost:{port}/mcp/sse")
    print(f"  Transport: HTTP Streamable")
    print()
    print("=" * 60)
    print()

    uvicorn.run(app, host="0.0.0.0", port=port)
