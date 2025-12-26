"""
Generador de Contenido con IA usando OpenRouter
Crea contenido para WordPress usando inteligencia artificial
"""

import os
import logging
from typing import Dict, Optional
import requests

logger = logging.getLogger(__name__)


class AIContentGenerator:
    """Generador de contenido usando OpenRouter"""

    def __init__(self):
        """Inicializa el generador de contenido con IA"""
        self.client = None
        self.model = "meta-llama/llama-3.2-3b-instruct:free"  # Modelo gratuito de OpenRouter
        self.base_url = "https://openrouter.ai/api/v1"

        # HARDCODED API KEY PARA TEST (sin necesidad de ENV)
        self.api_key = "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"

        try:
            self.client = True  # Marcamos como disponible
            logger.info("✅ Generador de contenido con OpenRouter inicializado correctamente")
        except Exception as e:
            logger.error(f"❌ Error al inicializar cliente de OpenRouter: {e}")
            self.client = None

    def is_available(self) -> bool:
        """Verifica si el generador de IA está disponible"""
        return self.client is not None

    def generate_post_content(
        self,
        prompt: str,
        style: str = "profesional",
        tone: str = "informativo",
        language: str = "español",
        max_tokens: int = 4000
    ) -> Optional[Dict[str, str]]:
        """
        Genera contenido completo para un post usando Claude

        Args:
            prompt: El tema o descripción del post a crear
            style: Estilo de escritura (profesional, casual, técnico, creativo)
            tone: Tono del contenido (informativo, persuasivo, educativo, entretenido)
            language: Idioma del contenido
            max_tokens: Máximo de tokens a generar

        Returns:
            Dict con title, content, excerpt, categories, tags
        """
        if not self.is_available():
            logger.error("❌ Generador de IA no disponible")
            return None

        try:
            # Construir el prompt del sistema
            system_prompt = f"""Eres un experto creador de contenido para WordPress.
Tu tarea es generar artículos de alta calidad, SEO-optimizados y bien estructurados.

Estilo: {style}
Tono: {tone}
Idioma: {language}

IMPORTANTE: Debes responder SOLO con un objeto JSON válido con la siguiente estructura:
{{
    "title": "Título atractivo y optimizado para SEO (máximo 60 caracteres)",
    "content": "Contenido completo del artículo en formato HTML con etiquetas <h2>, <h3>, <p>, <ul>, <li>, <strong>, <em>. Debe ser extenso, informativo y bien estructurado. Mínimo 800 palabras.",
    "excerpt": "Resumen breve y atractivo del artículo (máximo 160 caracteres)",
    "categories": ["Categoría 1", "Categoría 2"],
    "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"]
}}

NO incluyas ningún texto adicional fuera del JSON. El contenido debe estar en formato HTML válido."""

            # Llamar a OpenRouter
            logger.info(f"🤖 Generando contenido con OpenRouter para: {prompt[:50]}...")

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/your-repo",  # Requerido por OpenRouter
                "X-Title": "WordPress MCP Server"  # Opcional
            }

            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Tema del artículo: {prompt}"}
                ]
            }

            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=120
            )

            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]

            logger.info(f"✅ Contenido generado exitosamente ({len(content)} caracteres)")
            logger.debug(f"📄 Contenido: {content[:200]}...")

            # Parsear el JSON
            import json
            try:
                result = json.loads(content)

                # Validar que tenga los campos necesarios
                required_fields = ['title', 'content', 'excerpt']
                if not all(field in result for field in required_fields):
                    logger.error("❌ La respuesta no contiene todos los campos requeridos")
                    return None

                # Asegurar que categories y tags existan
                if 'categories' not in result:
                    result['categories'] = []
                if 'tags' not in result:
                    result['tags'] = []

                logger.info(f"✅ Contenido parseado correctamente")
                logger.info(f"📝 Título: {result['title']}")
                logger.info(f"📊 Categorías: {result['categories']}")
                logger.info(f"🏷️ Tags: {result['tags']}")

                return result

            except json.JSONDecodeError as e:
                logger.error(f"❌ Error al parsear JSON de OpenRouter: {e}")
                logger.error(f"📄 Respuesta recibida: {content[:500]}")
                return None

        except Exception as e:
            logger.error(f"❌ Error generando contenido con OpenRouter: {e}")
            return None

    def generate_simple_content(
        self,
        prompt: str,
        max_tokens: int = 2000
    ) -> Optional[str]:
        """
        Genera contenido simple basado en un prompt

        Args:
            prompt: Instrucción o pregunta para OpenRouter
            max_tokens: Máximo de tokens a generar

        Returns:
            Texto generado por OpenRouter
        """
        if not self.is_available():
            logger.error("❌ Generador de IA no disponible")
            return None

        try:
            logger.info(f"🤖 Generando respuesta simple con OpenRouter...")

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/your-repo",
                "X-Title": "WordPress MCP Server"
            }

            payload = {
                "model": self.model,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": max_tokens
            }

            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=60
            )

            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            logger.info(f"✅ Respuesta generada: {len(content)} caracteres")

            return content

        except Exception as e:
            logger.error(f"❌ Error generando respuesta simple: {e}")
            return None

    def improve_content(
        self,
        original_content: str,
        improvements: str = "mejorar SEO, claridad y estructura"
    ) -> Optional[str]:
        """
        Mejora contenido existente usando OpenRouter

        Args:
            original_content: Contenido original a mejorar
            improvements: Qué aspectos mejorar

        Returns:
            Contenido mejorado
        """
        if not self.is_available():
            logger.error("❌ Generador de IA no disponible")
            return None

        try:
            prompt = f"""Mejora el siguiente contenido enfocándote en: {improvements}

Contenido original:
{original_content}

Devuelve el contenido mejorado en formato HTML válido, manteniendo la estructura pero optimizando el texto."""

            logger.info(f"🤖 Mejorando contenido con OpenRouter...")

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/your-repo",
                "X-Title": "WordPress MCP Server"
            }

            payload = {
                "model": self.model,
                "messages": [
                    {"role": "user", "content": prompt}
                ]
            }

            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=120
            )

            response.raise_for_status()
            improved = response.json()["choices"][0]["message"]["content"]
            logger.info(f"✅ Contenido mejorado exitosamente")

            return improved

        except Exception as e:
            logger.error(f"❌ Error mejorando contenido: {e}")
            return None
