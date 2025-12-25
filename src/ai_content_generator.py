"""
Generador de Contenido con IA usando Claude (Anthropic)
Crea contenido para WordPress usando inteligencia artificial
"""

import os
import logging
from typing import Dict, Optional
from anthropic import Anthropic

logger = logging.getLogger(__name__)


class AIContentGenerator:
    """Generador de contenido usando Claude de Anthropic"""

    def __init__(self):
        """Inicializa el generador de contenido con IA"""
        self.client = None
        self.model = "claude-3-5-sonnet-20241022"  # Modelo más reciente y potente

        # Inicializar cliente de Anthropic si la API key está disponible
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if api_key:
            try:
                self.client = Anthropic(api_key=api_key)
                logger.info("✅ Generador de contenido con Claude inicializado correctamente")
            except Exception as e:
                logger.error(f"❌ Error al inicializar cliente de Anthropic: {e}")
                self.client = None
        else:
            logger.warning("⚠️ ANTHROPIC_API_KEY no encontrada - generación de contenido IA deshabilitada")

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

            # Llamar a Claude
            logger.info(f"🤖 Generando contenido con Claude para: {prompt[:50]}...")

            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            # Extraer el contenido
            content = response.content[0].text

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
                logger.error(f"❌ Error al parsear JSON de Claude: {e}")
                logger.error(f"📄 Respuesta recibida: {content[:500]}")
                return None

        except Exception as e:
            logger.error(f"❌ Error generando contenido con Claude: {e}")
            return None

    def generate_simple_content(
        self,
        prompt: str,
        max_tokens: int = 2000
    ) -> Optional[str]:
        """
        Genera contenido simple basado en un prompt

        Args:
            prompt: Instrucción o pregunta para Claude
            max_tokens: Máximo de tokens a generar

        Returns:
            Texto generado por Claude
        """
        if not self.is_available():
            logger.error("❌ Generador de IA no disponible")
            return None

        try:
            logger.info(f"🤖 Generando respuesta simple con Claude...")

            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            content = response.content[0].text
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
        Mejora contenido existente usando Claude

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

            logger.info(f"🤖 Mejorando contenido con Claude...")

            response = self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            improved = response.content[0].text
            logger.info(f"✅ Contenido mejorado exitosamente")

            return improved

        except Exception as e:
            logger.error(f"❌ Error mejorando contenido: {e}")
            return None
