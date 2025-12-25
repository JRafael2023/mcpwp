# Servidor MCP de WordPress con IA 🚀🤖

[![MCP](https://img.shields.io/badge/MCP-1.0-blue.svg)](https://modelcontextprotocol.io)
[![Python](https://img.shields.io/badge/Python-3.8+-green.svg)](https://www.python.org)
[![Claude](https://img.shields.io/badge/Claude-Sonnet%204.5-orange.svg)](https://www.anthropic.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Un servidor del Protocolo de Contexto de Modelo (MCP) que permite administrar sitios WordPress con **generación de contenido usando IA (Claude/Anthropic)** integrada.

![WordPress + AI = Magia](https://img.shields.io/badge/WordPress-AI%20Powered-21759B?style=for-the-badge&logo=wordpress&logoColor=white)

## ✨ Características

### 🌐 Gestión de WordPress
- **Control completo** de tu sitio WordPress
- **Operaciones CRUD** - Lista, crea, actualiza y elimina posts
- **Gestión de taxonomías** - Categorías y etiquetas
- **Gestión de medios** - Sube archivos multimedia
- **Autenticación segura** - Usa contraseñas de aplicación de WordPress

### 🤖 IA Integrada (Claude/Anthropic)
- **Generación automática de contenido** - Solo proporciona un prompt, la IA genera todo
- **Optimización SEO** - Contenido optimizado para buscadores
- **Mejora de posts existentes** - Optimiza contenido ya publicado
- **Multilingüe** - Genera contenido en cualquier idioma
- **Estilos y tonos personalizables** - Profesional, casual, técnico, creativo

### 🎯 Arquitectura Centralizada
- **Tokens del dueño** - Los usuarios NO necesitan API keys propias
- **Un solo punto de configuración** - Tu ANTHROPIC_API_KEY en el servidor
- **Escalable** - Múltiples usuarios usando tus credenciales de IA
- **Más rápido** - Todo en una sola llamada desde n8n u otros clientes

## 🚀 Dos Modos de Uso

### 1️⃣ Modo MCP (Claude Desktop, Cline, etc.)
Usa el servidor MCP tradicional para integrar con herramientas que soporten el protocolo MCP.

### 2️⃣ Modo HTTP/REST API (n8n, Zapier, Make.com, etc.) ⭐ NUEVO
Despliega el servidor como una API HTTP en Render y úsalo desde **cualquier herramienta**:
- **n8n** - Workflows automatizados
- **Zapier/Make.com** - Automatizaciones sin código
- **Postman** - Testing y desarrollo
- **Cualquier app** - Solo necesitas hacer HTTP requests

👉 **[Ver guía completa de despliegue en Render](DEPLOY_RENDER.md)**

## 🎯 Casos de Uso

### Para Propietarios de SaaS
- **Ofrece generación de contenido con IA** sin que tus usuarios necesiten API keys
- **Controla los costos** - Tú pagas y cobras como prefieras
- **Integración con n8n** - Workflows automatizados perfectos
- **Despliega en Render** - $7/mes para servicio siempre activo

### Para Bloggers y Creadores
- **Genera posts completos** con un simple prompt
- **Optimiza contenido existente** automáticamente
- **Publicación multilingüe** sin esfuerzo
- **Automatiza tu blog** - Posts diarios automáticos desde n8n

### Para Agencias
- **Gestiona múltiples sitios WordPress**
- **Crea contenido en lote** con IA
- **Automatiza flujos de trabajo** completos
- **Integra con Google Sheets** - Tus clientes solo agregan temas

## 📋 Requisitos Previos

- Python 3.8 o superior
- Sitio WordPress con REST API habilitado
- Cuenta de Anthropic con API key (para usar Claude)
- Cliente MCP: n8n, Claude Desktop, o cualquier compatible

## 🚀 Inicio Rápido

### 1. Clonar e Instalar

```bash
git clone https://github.com/seomentor/wpmcp.git
cd wpmcp
pip install -r requirements.txt
```

### 2. Configurar Variables de Entorno

Crea un archivo `.env` basándote en `.env.example`:

```env
# WordPress
WP_URL=https://tu-sitio-wordpress.com
WP_USERNAME=tu-usuario
WP_PASSWORD=tu-contraseña-de-aplicación

# IA - Claude (Anthropic)
ANTHROPIC_API_KEY=sk-ant-api03-xxxxxxxxxxxxx
```

**⚠️ Importante:**
- Usa una **contraseña de aplicación** de WordPress (no tu contraseña normal)
- Tu `ANTHROPIC_API_KEY` es **TUYA** (del dueño del servidor)
- Los usuarios finales **NO necesitan** sus propias API keys

### 3. Configurar el Cliente MCP

#### Opción A: Usar con n8n (Recomendado para producción)

1. Instala el nodo MCP en n8n
2. Configura el endpoint:
   ```
   Endpoint: http://tu-servidor:puerto/mcp
   Transport: HTTP Streamable
   Authentication: Multiple Headers Auth
   ```
3. Los usuarios solo envían **prompts**, tú controlas la IA

#### Opción B: Usar con Claude Desktop (Para desarrollo)

Añade a tu configuración de Claude Desktop:

**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
**Mac**: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "wordpress-ai": {
      "command": "python",
      "args": ["-m", "src.server"],
      "cwd": "C:/ruta/a/wpmcp",
      "env": {
        "WP_URL": "https://tu-sitio.com",
        "WP_USERNAME": "usuario",
        "WP_PASSWORD": "contraseña-aplicacion",
        "ANTHROPIC_API_KEY": "sk-ant-api03-xxxxx"
      }
    }
  }
}
```

### 4. ¡Comienza a Usar!

**Desde n8n:**
```javascript
// Solo envía un prompt
{
  "tool": "generate_post_with_ai",
  "arguments": {
    "prompt": "Escribe un artículo sobre las ventajas de la IA en medicina"
  }
}
```

**Desde Claude Desktop:**
```
"Genera un post sobre tendencias de IA"
"Lista todos los posts"
"Mejora el post 123 para mejor SEO"
```

## 📚 Documentación

### Herramientas Disponibles

#### 🔹 Gestión Básica de WordPress

| Herramienta | Descripción |
|-------------|-------------|
| `list_categories` | Lista todas las categorías |
| `list_posts` | Lista posts con paginación |
| `search_posts` | Busca posts por término |
| `create_post` | Crea un post manual |
| `update_post` | Actualiza post existente |
| `delete_post` | Elimina un post |
| `upload_media` | Sube archivo multimedia |
| `list_tags` | Lista todas las etiquetas |
| `search_tags` | Busca etiquetas |
| `create_tag` | Crea una etiqueta |

#### 🤖 Herramientas con IA (NUEVAS)

| Herramienta | Descripción | Ejemplo |
|-------------|-------------|---------|
| **`generate_post_with_ai`** | Genera y publica un post completo usando IA | `{"prompt": "Artículo sobre blockchain"}` |
| **`improve_post_with_ai`** | Mejora un post existente con IA | `{"post_id": 123, "improvements": "mejorar SEO"}` |
| **`generate_content_from_prompt`** | Genera contenido sin publicar (solo JSON) | `{"prompt": "Guía de Python"}` |

### Ejemplos de Uso

#### Generar Post Completo con IA

```json
{
  "tool": "generate_post_with_ai",
  "arguments": {
    "prompt": "Escribe un artículo completo sobre las ventajas de la inteligencia artificial en la medicina moderna",
    "style": "profesional",
    "tone": "informativo",
    "language": "español",
    "status": "draft"
  }
}
```

**La IA generará automáticamente:**
- ✅ Título optimizado para SEO
- ✅ Contenido extenso y bien estructurado (HTML)
- ✅ Extracto atractivo
- ✅ Categorías relevantes
- ✅ Tags apropiados
- ✅ Todo publicado directamente en WordPress

#### Mejorar Post Existente

```json
{
  "tool": "improve_post_with_ai",
  "arguments": {
    "post_id": 123,
    "improvements": "mejorar SEO, claridad y añadir más ejemplos prácticos"
  }
}
```

#### Generar Contenido sin Publicar

```json
{
  "tool": "generate_content_from_prompt",
  "arguments": {
    "prompt": "Tutorial paso a paso sobre instalación de Docker",
    "style": "técnico",
    "tone": "educativo"
  }
}
```

### Parámetros de Personalización

**Estilos disponibles:**
- `profesional` - Lenguaje formal y corporativo
- `casual` - Lenguaje relajado y cercano
- `técnico` - Lenguaje especializado y preciso
- `creativo` - Lenguaje original y artístico

**Tonos disponibles:**
- `informativo` - Objetivo y educativo
- `persuasivo` - Convence y motiva a la acción
- `educativo` - Enseña paso a paso
- `entretenido` - Divertido y engaging

## 🔧 Configuración de WordPress

### 1. Habilitar REST API
Habilitado por defecto en WordPress 5.0+

### 2. Crear Contraseña de Aplicación
1. Ve a **Usuarios → Perfil**
2. Baja a **Contraseñas de Aplicación**
3. Ingresa un nombre (ej: "MCP Server")
4. Copia la contraseña generada

### 3. Permisos Requeridos
- `edit_posts` - Crear y editar posts
- `upload_files` - Subir multimedia
- `manage_categories` - Gestionar categorías
- `manage_post_tags` - Gestionar etiquetas

## 💰 Costos de IA (Claude/Anthropic)

### Claude 3.5 Sonnet (Modelo usado)
- **Input:** ~$3 por 1M tokens
- **Output:** ~$15 por 1M tokens

### Estimación por post:
- Post típico (1000 palabras): ~$0.05 - $0.15
- Post largo (2000+ palabras): ~$0.15 - $0.30

**💡 Tip:** Como dueño del servidor, tú controlas estos costos y puedes:
- Cobrar a tus usuarios por post generado
- Incluirlo en un plan de suscripción
- Ofrecer X posts gratis por mes

## 🔄 Cambiar a OpenAI (Opcional)

Si prefieres usar GPT en lugar de Claude:

1. Edita `src/ai_content_generator.py`
2. Reemplaza el cliente de Anthropic por OpenAI
3. Actualiza `.env`:
   ```env
   OPENAI_API_KEY=sk-xxxxxxxxxxxxx
   ```
4. Actualiza `requirements.txt`:
   ```
   openai>=1.0.0
   ```

## 🐛 Solución de Problemas

### "Generador de IA no disponible"
- ✅ Verifica que `ANTHROPIC_API_KEY` esté en `.env`
- ✅ Verifica que la API key sea válida en console.anthropic.com
- ✅ Reinicia el servidor MCP

### "Error generando contenido"
- ✅ Verifica tu saldo de créditos en Anthropic
- ✅ Revisa los logs para ver el error específico
- ✅ Verifica que el prompt sea claro y específico

### "Error creando post en WordPress"
- ✅ Verifica los permisos del usuario de WordPress
- ✅ Asegúrate de que el REST API esté habilitado
- ✅ Verifica que las categorías/tags existan o puedan crearse

## 📊 Arquitectura del Sistema

```
┌─────────────┐
│   Usuario   │
│   (n8n)     │
└──────┬──────┘
       │ Prompt simple
       ▼
┌─────────────────────────┐
│  Servidor MCP           │
│  ┌──────────────────┐   │
│  │ Tu ANTHROPIC_KEY │   │  ← Tus credenciales
│  └────────┬─────────┘   │
│           ▼             │
│  ┌──────────────────┐   │
│  │  Claude IA       │   │
│  │  (Genera         │   │
│  │   contenido)     │   │
│  └────────┬─────────┘   │
│           ▼             │
│  ┌──────────────────┐   │
│  │  WordPress API   │   │
│  │  (Publica)       │   │
│  └──────────────────┘   │
└─────────────────────────┘
       │
       ▼
┌─────────────┐
│  WordPress  │
│    Blog     │
└─────────────┘
```

## 🤝 Contribuir

¡Las contribuciones son bienvenidas!

1. Fork el repositorio
2. Crea tu rama (`git checkout -b feature/CaracteristicaIncreible`)
3. Commit tus cambios (`git commit -m 'Añadir CaracteristicaIncreible'`)
4. Push a la rama (`git push origin feature/CaracteristicaIncreible`)
5. Abre un Pull Request

## 📄 Licencia

MIT License - consulta [LICENSE](LICENSE) para más detalles.

## 🙏 Agradecimientos

- [Model Context Protocol](https://modelcontextprotocol.io) por Anthropic
- [WordPress REST API](https://developer.wordpress.org/rest-api/)
- [Claude AI](https://www.anthropic.com) por Anthropic
- [n8n](https://n8n.io) por la integración MCP

## 📞 Soporte

- 📧 Email: shay@seomentor.co.il
- 🐛 Issues: [GitHub Issues](https://github.com/seomentor/wpmcp/issues)
- 💬 Discusiones: [GitHub Discussions](https://github.com/seomentor/wpmcp/discussions)

---

**Hecho con ❤️ para desarrolladores, SEOs y emprendedores de SaaS**

Visita mi sitio: https://www.seomentor.co.il

---

## ⭐ Diferenciadores Clave

### vs. Otras Soluciones MCP WordPress:
✅ **IA integrada en el servidor** (no en el cliente)
✅ **Usuario solo envía prompts** (no necesita configurar IA)
✅ **Tú controlas los costos** de IA
✅ **Perfecto para SaaS** y servicios escalables
✅ **Compatible con n8n** para automatización total

### Ideal para:
- 🏢 SaaS de generación de contenido
- 🤖 Automatizaciones con n8n
- 📝 Agencias de contenido
- 🚀 Emprendedores que quieren ofrecer IA sin complejidad
