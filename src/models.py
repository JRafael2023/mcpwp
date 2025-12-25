"""
Modelos del Servidor MCP de WordPress
Modelos de datos para operaciones de WordPress y respuestas del API
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from dataclasses import dataclass

@dataclass
class WordPressPost:
    """Datos del post de WordPress"""
    title: str
    content: str
    status: str = "draft"
    excerpt: str = ""
    categories: Optional[List[int]] = None
    tags: Optional[List[int]] = None

@dataclass
class ArticleResponse:
    """Respuesta de la creación de artículo"""
    success: bool
    message: str
    post_id: Optional[int] = None
    url: Optional[str] = None

class ArticleRequest(BaseModel):
    """Petición para crear un artículo"""
    title: str = Field(description="Título del artículo")
    content: str = Field(description="Contenido del artículo")
    excerpt: Optional[str] = Field(default=None, description="Extracto")
    categories: Optional[List[int]] = Field(default=None, description="IDs de categorías")
    tags: Optional[List[int]] = Field(default=None, description="IDs de etiquetas")
    status: str = Field(default="draft", description="Estado de publicación")
