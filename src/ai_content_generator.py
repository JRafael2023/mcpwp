"""
Generador de Contenido con IA usando Groq
Crea contenido para WordPress usando inteligencia artificial
"""

import os
import logging
from typing import Dict, Optional
import requests
import re

logger = logging.getLogger(__name__)


class AIContentGenerator:
    """Generador de contenido usando Groq"""

    def __init__(self):
        """Inicializa el generador de contenido con IA"""
        self.client = None
        self.model = "llama-3.3-70b-versatile"  # Modelo de Groq (gratis y rápido)
        self.base_url = "https://api.groq.com/openai/v1"

        # HARDCODED API KEY PARA TEST (sin necesidad de ENV)
        self.api_key = "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"

        try:
            self.client = True  # Marcamos como disponible
            logger.info("Generador de contenido con Groq inicializado correctamente")
        except Exception as e:
            logger.error(f"Error al inicializar cliente de Groq: {e}")
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
        Genera contenido completo para un post usando OpenRouter

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
            logger.error("Generador de IA no disponible")
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

            # Llamar a Groq
            logger.info(f"Generando contenido con Groq para: {prompt[:50]}...")

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
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

            logger.info(f"Contenido generado exitosamente ({len(content)} caracteres)")
            logger.debug(f"Contenido: {content[:200]}...")

            # Parsear el JSON (remover bloques de código markdown si existen)
            import json

            # Limpiar bloques de código markdown
            content_clean = content.strip()
            if content_clean.startswith("```"):
                # Remover ```json al inicio y ``` al final
                content_clean = re.sub(r'^```(?:json)?\s*\n?', '', content_clean)
                content_clean = re.sub(r'\n?```\s*$', '', content_clean)

            # SOLUCIÓN ROBUSTA: Escapar saltos de línea dentro de strings JSON
            # Esto convierte saltos literales en \n escapados
            in_string = False
            escape_next = False
            result_chars = []

            for i, char in enumerate(content_clean):
                if escape_next:
                    result_chars.append(char)
                    escape_next = False
                    continue

                if char == '\\':
                    escape_next = True
                    result_chars.append(char)
                    continue

                if char == '"':
                    in_string = not in_string
                    result_chars.append(char)
                    continue

                # Si estamos dentro de un string y encontramos un salto de línea, escaparlo
                if in_string and char == '\n':
                    result_chars.append('\\n')
                elif in_string and char == '\r':
                    # Ignorar \r
                    continue
                elif in_string and char == '\t':
                    result_chars.append('\\t')
                else:
                    result_chars.append(char)

            content_clean = ''.join(result_chars)

            try:
                result = json.loads(content_clean)

                # Validar que tenga los campos necesarios
                required_fields = ['title', 'content', 'excerpt']
                if not all(field in result for field in required_fields):
                    logger.error("La respuesta no contiene todos los campos requeridos")
                    return None

                # Asegurar que categories y tags existan
                if 'categories' not in result:
                    result['categories'] = []
                if 'tags' not in result:
                    result['tags'] = []

                logger.info(f"Contenido parseado correctamente")
                logger.info(f"Titulo: {result['title']}")
                logger.info(f"Categorias: {result['categories']}")
                logger.info(f"Tags: {result['tags']}")

                return result

            except json.JSONDecodeError as e:
                logger.error(f"Error al parsear JSON de Groq: {e}")
                logger.error(f"Respuesta recibida: {content[:500]}")
                return None

        except Exception as e:
            logger.error(f"Error generando contenido con Groq: {e}")
            return None

    def generate_simple_content(
        self,
        prompt: str,
        max_tokens: int = 2000
    ) -> Optional[str]:
        """
        Genera contenido simple basado en un prompt

        Args:
            prompt: Instrucción o pregunta para Groq
            max_tokens: Máximo de tokens a generar

        Returns:
            Texto generado por Groq
        """
        if not self.is_available():
            logger.error("Generador de IA no disponible")
            return None

        try:
            logger.info(f"Generando respuesta simple con Groq...")

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
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
            logger.info(f"Respuesta generada: {len(content)} caracteres")

            return content

        except Exception as e:
            logger.error(f"Error generando respuesta simple: {e}")
            return None

    def improve_content(
        self,
        original_content: str,
        improvements: str = "mejorar SEO, claridad y estructura"
    ) -> Optional[str]:
        """
        Mejora contenido existente usando Groq

        Args:
            original_content: Contenido original a mejorar
            improvements: Qué aspectos mejorar

        Returns:
            Contenido mejorado
        """
        if not self.is_available():
            logger.error("Generador de IA no disponible")
            return None

        try:
            prompt = f"""Mejora el siguiente contenido enfocándote en: {improvements}

Contenido original:
{original_content}

Devuelve el contenido mejorado en formato HTML válido, manteniendo la estructura pero optimizando el texto."""

            logger.info(f"Mejorando contenido con Groq...")

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
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
            logger.info(f"Contenido mejorado exitosamente")

            return improved

        except Exception as e:
            logger.error(f"Error mejorando contenido: {e}")
            return None
