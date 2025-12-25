#!/usr/bin/env python3
"""
Servidor HTTP (REST API) para exponer el MCP de WordPress
Permite usar las herramientas del MCP como endpoints HTTP simples
Perfecto para integrar con n8n, Zapier, Make.com, etc.
"""

import os
import asyncio
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Importar el servidor MCP y clases necesarias
from .server import WordPressAPI
from .ai_content_generator import AIContentGenerator

# Cargar variables de entorno
load_dotenv()

# Crear aplicación FastAPI
app = FastAPI(
    title="WordPress MCP HTTP API",
    description="API HTTP para gestión de WordPress con IA integrada",
    version="3.0.0"
)

# Configurar CORS para permitir requests desde n8n
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especifica los dominios permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inicializar clientes globales
wp_client: Optional[WordPressAPI] = None
ai_generator: Optional[AIContentGenerator] = None


# === Modelos de Request ===

class GeneratePostRequest(BaseModel):
    """Request para generar un post con IA"""
    prompt: str
    style: str = "profesional"
    tone: str = "informativo"
    language: str = "español"
    status: str = "draft"


class CreatePostRequest(BaseModel):
    """Request para crear un post manual"""
    title: str
    content: str
    status: str = "draft"
    categories: Optional[list] = None
    tags: Optional[list] = None


class ImprovePostRequest(BaseModel):
    """Request para mejorar un post con IA"""
    post_id: int
    improvements: str = "mejorar SEO, claridad y estructura"


# === Eventos de inicio ===

@app.on_event("startup")
async def startup_event():
    """Inicializa los clientes al arrancar el servidor"""
    global wp_client, ai_generator

    # Verificar variables de entorno
    wp_url = os.getenv('WP_URL')
    wp_username = os.getenv('WP_USERNAME')
    wp_password = os.getenv('WP_PASSWORD')

    if not all([wp_url, wp_username, wp_password]):
        raise RuntimeError("Faltan credenciales de WordPress en variables de entorno")

    # Inicializar cliente de WordPress
    wp_client = WordPressAPI(wp_url, wp_username, wp_password)
    print(f"✅ WordPress client inicializado: {wp_url}")

    # Inicializar generador de IA (opcional)
    try:
        ai_generator = AIContentGenerator()
        if ai_generator.is_available():
            print("✅ Generador de IA disponible")
        else:
            print("⚠️  Generador de IA NO disponible (falta ANTHROPIC_API_KEY)")
    except Exception as e:
        print(f"⚠️  Error inicializando IA: {e}")
        ai_generator = None


# === Endpoints de Salud ===

@app.get("/")
async def root():
    """Endpoint raíz - información del servidor"""
    return {
        "name": "WordPress MCP HTTP API",
        "version": "3.0.0",
        "status": "running",
        "ai_available": ai_generator.is_available() if ai_generator else False,
        "wordpress_url": os.getenv('WP_URL')
    }


@app.get("/health")
async def health_check():
    """Health check para Render y otros servicios"""
    return {
        "status": "healthy",
        "wordpress": wp_client is not None,
        "ai": ai_generator.is_available() if ai_generator else False
    }


# === Endpoints de IA ===

@app.post("/ai/generate-post")
async def generate_post_with_ai(request: GeneratePostRequest):
    """
    Genera y publica un post completo usando IA

    Ejemplo de uso desde n8n:
    POST https://tu-app.render.com/ai/generate-post
    Body: {
        "prompt": "Escribe sobre los beneficios del café",
        "style": "casual",
        "tone": "informativo",
        "status": "draft"
    }
    """
    if not ai_generator or not ai_generator.is_available():
        raise HTTPException(
            status_code=503,
            detail="Generador de IA no disponible. Configure ANTHROPIC_API_KEY"
        )

    if not wp_client:
        raise HTTPException(status_code=500, detail="Cliente de WordPress no inicializado")

    try:
        # Generar contenido con IA
        ai_content = ai_generator.generate_post_content(
            prompt=request.prompt,
            style=request.style,
            tone=request.tone,
            language=request.language
        )

        if not ai_content:
            raise HTTPException(status_code=500, detail="Error generando contenido con IA")

        # Crear categorías si no existen
        category_ids = []
        if ai_content.get('categories'):
            for cat_name in ai_content['categories']:
                cats = await wp_client.list_categories(per_page=100)
                found = False
                for cat in cats:
                    if cat.get('name', '').lower() == cat_name.lower():
                        category_ids.append(cat['id'])
                        found = True
                        break

        # Crear tags si no existen
        tag_ids = []
        if ai_content.get('tags'):
            for tag_name in ai_content['tags']:
                tags = await wp_client.list_tags(per_page=100)
                found = False
                for tag in tags:
                    if tag.get('name', '').lower() == tag_name.lower():
                        tag_ids.append(tag['id'])
                        found = True
                        break

                if not found:
                    try:
                        new_tag = await wp_client.create_tag(name=tag_name)
                        tag_ids.append(new_tag['id'])
                    except:
                        pass

        # Crear post en WordPress
        post_result = await wp_client.create_post(
            title=ai_content['title'],
            content=ai_content['content'],
            status=request.status,
            categories=category_ids if category_ids else None,
            tags=tag_ids if tag_ids else None
        )

        # Añadir información extra
        return {
            "success": True,
            "post_id": post_result.get('id'),
            "title": post_result.get('title', {}).get('rendered', 'N/A'),
            "link": post_result.get('link'),
            "status": post_result.get('status'),
            "ai_generated": True,
            "ai_categories": ai_content.get('categories', []),
            "ai_tags": ai_content.get('tags', []),
            "excerpt": ai_content.get('excerpt', '')
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.post("/ai/generate-content")
async def generate_content_only(request: GeneratePostRequest):
    """
    Genera contenido con IA SIN publicar
    Útil para preview o edición manual antes de publicar
    """
    if not ai_generator or not ai_generator.is_available():
        raise HTTPException(
            status_code=503,
            detail="Generador de IA no disponible. Configure ANTHROPIC_API_KEY"
        )

    try:
        ai_content = ai_generator.generate_post_content(
            prompt=request.prompt,
            style=request.style,
            tone=request.tone,
            language=request.language
        )

        if not ai_content:
            raise HTTPException(status_code=500, detail="Error generando contenido")

        return {
            "success": True,
            "ai_generated": True,
            "content": ai_content
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.post("/ai/improve-post")
async def improve_post(request: ImprovePostRequest):
    """Mejora un post existente usando IA"""
    if not ai_generator or not ai_generator.is_available():
        raise HTTPException(
            status_code=503,
            detail="Generador de IA no disponible. Configure ANTHROPIC_API_KEY"
        )

    if not wp_client:
        raise HTTPException(status_code=500, detail="Cliente de WordPress no inicializado")

    try:
        # Obtener post actual (simplificado)
        posts = await wp_client.list_posts(per_page=100)
        current_post = None

        for post in posts:
            if post.get('id') == request.post_id:
                current_post = post
                break

        if not current_post:
            raise HTTPException(status_code=404, detail=f"Post {request.post_id} no encontrado")

        # Mejorar contenido
        current_content = current_post.get('content', {}).get('rendered', '')
        improved_content = ai_generator.improve_content(
            original_content=current_content,
            improvements=request.improvements
        )

        if not improved_content:
            raise HTTPException(status_code=500, detail="Error mejorando contenido")

        # Actualizar post
        result = await wp_client.update_post(
            post_id=request.post_id,
            content=improved_content
        )

        return {
            "success": True,
            "post_id": result.get('id'),
            "ai_improved": True,
            "link": result.get('link')
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


# === Endpoints de WordPress (sin IA) ===

@app.post("/posts/create")
async def create_post(request: CreatePostRequest):
    """Crea un post manualmente (sin IA)"""
    if not wp_client:
        raise HTTPException(status_code=500, detail="Cliente de WordPress no inicializado")

    try:
        result = await wp_client.create_post(
            title=request.title,
            content=request.content,
            status=request.status,
            categories=request.categories,
            tags=request.tags
        )

        return {
            "success": True,
            "post_id": result.get('id'),
            "title": result.get('title', {}).get('rendered', 'N/A'),
            "link": result.get('link'),
            "status": result.get('status')
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.get("/posts")
async def list_posts(per_page: int = 10, page: int = 1):
    """Lista posts de WordPress"""
    if not wp_client:
        raise HTTPException(status_code=500, detail="Cliente de WordPress no inicializado")

    try:
        posts = await wp_client.list_posts(per_page=per_page, page=page)
        return {"success": True, "posts": posts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.get("/categories")
async def list_categories(per_page: int = 100):
    """Lista categorías de WordPress"""
    if not wp_client:
        raise HTTPException(status_code=500, detail="Cliente de WordPress no inicializado")

    try:
        categories = await wp_client.list_categories(per_page=per_page)
        return {"success": True, "categories": categories}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.get("/tags")
async def list_tags(per_page: int = 100):
    """Lista tags de WordPress"""
    if not wp_client:
        raise HTTPException(status_code=500, detail="Cliente de WordPress no inicializado")

    try:
        tags = await wp_client.list_tags(per_page=per_page)
        return {"success": True, "tags": tags}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


# === Main ===

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv('PORT', 8000))

    print("=" * 60)
    print("🚀 WordPress MCP HTTP Server")
    print("=" * 60)
    print(f"Puerto: {port}")
    print(f"WordPress: {os.getenv('WP_URL')}")
    print(f"IA disponible: {os.getenv('ANTHROPIC_API_KEY', 'NO')[:10]}...")
    print()
    print("Endpoints principales:")
    print(f"  POST /ai/generate-post  - Generar post con IA")
    print(f"  POST /posts/create      - Crear post manual")
    print(f"  GET  /posts             - Listar posts")
    print()

    uvicorn.run(app, host="0.0.0.0", port=port)
