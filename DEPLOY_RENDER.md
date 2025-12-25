# Guía de Despliegue en Render

Esta guía te muestra cómo desplegar tu servidor MCP de WordPress como una API HTTP en Render y conectarlo con n8n.

## 📋 Pre-requisitos

- Cuenta en [Render.com](https://render.com) (gratis)
- Tu repositorio en GitHub
- Credenciales de WordPress
- API Key de Anthropic (opcional, solo para IA)

## 🚀 Paso 1: Preparar el Repositorio

1. **Asegúrate de tener todos los archivos necesarios**:
   - `src/http_server.py` ✅
   - `render.yaml` ✅
   - `Procfile` ✅
   - `requirements.txt` ✅

2. **Haz commit y push a GitHub**:
   ```bash
   git add .
   git commit -m "Add HTTP server for Render deployment"
   git push origin main
   ```

## 🌐 Paso 2: Desplegar en Render

### Opción A: Usando render.yaml (Recomendado)

1. Ve a [Render Dashboard](https://dashboard.render.com/)
2. Click en **"New +"** → **"Blueprint"**
3. Conecta tu repositorio de GitHub
4. Render detectará automáticamente el archivo `render.yaml`
5. Click en **"Apply"**

### Opción B: Despliegue Manual

1. Ve a [Render Dashboard](https://dashboard.render.com/)
2. Click en **"New +"** → **"Web Service"**
3. Conecta tu repositorio de GitHub
4. Configura:
   - **Name**: `wordpress-mcp-api` (o el que prefieras)
   - **Region**: Oregon (o el más cercano)
   - **Branch**: `main`
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python -m src.http_server`
   - **Instance Type**: Free

## 🔐 Paso 3: Configurar Variables de Entorno

En Render, ve a tu servicio → **Environment** y añade:

```env
WP_URL=https://tu-sitio-wordpress.com
WP_USERNAME=admin
WP_PASSWORD=tu_password_de_aplicacion
ANTHROPIC_API_KEY=sk-ant-api03-xxxxxxxxxxxxx
PORT=10000
```

**IMPORTANTE**:
- `WP_PASSWORD` debe ser una **Contraseña de Aplicación**, no tu contraseña normal
- `ANTHROPIC_API_KEY` es opcional (solo si quieres usar IA)
- `PORT` normalmente es 10000 en Render

## ✅ Paso 4: Verificar el Despliegue

Una vez desplegado, tu servicio estará disponible en:
```
https://tu-app.onrender.com
```

Verifica que funciona visitando:
```
https://tu-app.onrender.com/health
```

Deberías ver algo como:
```json
{
  "status": "healthy",
  "wordpress": true,
  "ai": true
}
```

## 🔌 Paso 5: Conectar con n8n

### Método 1: Generar Post con IA (Simple)

1. En n8n, añade un nodo **HTTP Request**
2. Configura:
   - **Method**: POST
   - **URL**: `https://tu-app.onrender.com/ai/generate-post`
   - **Body Content Type**: JSON
   - **Body**:
     ```json
     {
       "prompt": "Escribe un artículo sobre los beneficios del café para la salud",
       "style": "casual",
       "tone": "informativo",
       "language": "español",
       "status": "draft"
     }
     ```

3. **Ejecuta** el workflow

**Respuesta esperada**:
```json
{
  "success": true,
  "post_id": 123,
  "title": "Los Increíbles Beneficios del Café para tu Salud",
  "link": "https://tu-wordpress.com/post-123",
  "status": "draft",
  "ai_generated": true,
  "ai_categories": ["Salud", "Bienestar"],
  "ai_tags": ["café", "salud", "beneficios"]
}
```

### Método 2: Workflow Completo con Trigger

**Ejemplo de workflow n8n**:

```
[Schedule Trigger] → [Set Variables] → [HTTP Request: Generate Post] → [Slack Notification]
```

1. **Schedule Trigger**: Ejecuta cada día a las 9am
2. **Set Variables**: Define el prompt dinámicamente
   ```json
   {
     "prompt": "Escribe sobre {{ $now.format('dddd') }}: tips de productividad"
   }
   ```
3. **HTTP Request**: Llama a `/ai/generate-post`
4. **Slack Notification**: Notifica cuando el post está listo

### Método 3: Usando Webhook

Puedes activar la creación de posts desde cualquier lugar:

1. **En n8n**: Añade un nodo **Webhook**
2. **Copia la URL del webhook**
3. **Añade un nodo HTTP Request** conectado al webhook
4. **Configura el HTTP Request** para llamar a tu API

Ahora puedes enviar un POST desde cualquier aplicación:
```bash
curl -X POST https://tu-n8n.com/webhook/crear-post \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Escribe sobre Python", "status": "publish"}'
```

## 📊 Endpoints Disponibles

### Con IA (requiere ANTHROPIC_API_KEY)

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/ai/generate-post` | POST | Genera y publica post con IA |
| `/ai/generate-content` | POST | Genera contenido sin publicar |
| `/ai/improve-post` | POST | Mejora un post existente |

### Sin IA (siempre disponibles)

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/posts/create` | POST | Crea post manualmente |
| `/posts` | GET | Lista posts |
| `/categories` | GET | Lista categorías |
| `/tags` | GET | Lista tags |
| `/health` | GET | Health check |

## 💡 Ejemplos de Uso en n8n

### Ejemplo 1: Blog Automático Diario

```json
{
  "nodes": [
    {
      "type": "n8n-nodes-base.scheduleTrigger",
      "name": "Cada día a las 9am",
      "parameters": {
        "rule": { "interval": [{ "field": "cronExpression", "expression": "0 9 * * *" }] }
      }
    },
    {
      "type": "n8n-nodes-base.httpRequest",
      "name": "Generar Post",
      "parameters": {
        "method": "POST",
        "url": "https://tu-app.onrender.com/ai/generate-post",
        "options": { "bodyContentType": "json" },
        "bodyParametersJson": {
          "prompt": "Escribe sobre tecnología y tendencias del día",
          "style": "profesional",
          "status": "publish"
        }
      }
    }
  ]
}
```

### Ejemplo 2: Desde Google Sheets

```
[Google Sheets Trigger] → [Loop] → [HTTP Request: Generate Post]
```

Cuando añades una fila nueva en Google Sheets con el tema, n8n genera el post automáticamente.

### Ejemplo 3: Content Pipeline con Aprobación

```
[Webhook] → [Generate Content] → [Slack: Pedir Aprobación] → [IF Approved] → [Create Post]
```

1. Genera contenido (sin publicar)
2. Envía preview a Slack
3. Espera aprobación
4. Si se aprueba, crea el post

## 🐛 Troubleshooting

### Error: "Cliente de WordPress no inicializado"
- Verifica que las variables `WP_URL`, `WP_USERNAME`, `WP_PASSWORD` estén configuradas en Render
- Reinicia el servicio en Render

### Error: "Generador de IA no disponible"
- Verifica que `ANTHROPIC_API_KEY` esté configurada
- Asegúrate de que la API key sea válida

### El servicio se duerme (plan Free)
- Render Free tier duerme después de 15min de inactividad
- Primera request después de dormir tarda ~1min en responder
- Solución: Upgrade a plan pago ($7/mes) o usa un cron job para mantenerlo activo

### Timeout en requests largos
- Posts largos con IA pueden tardar 30-60 segundos
- Aumenta el timeout en n8n: Settings → Timeout (ms) → 120000

## 💰 Costos

### Render
- **Free tier**: $0/mes (servicio se duerme después de 15min)
- **Starter**: $7/mes (siempre activo)

### Anthropic (IA)
- **Por post**: ~$0.05 - $0.30 dependiendo del largo
- **1000 posts/mes**: ~$50 - $300

### Total para SaaS
Si ofreces esto como servicio:
- **Infraestructura**: $7/mes (Render)
- **IA**: Variable según uso
- **Total**: Puedes cobrar $50-200/mes a clientes fácilmente

## 🎯 Próximos Pasos

1. **Añade autenticación**: Protege tu API con API keys
2. **Rate limiting**: Limita requests por IP
3. **Logging**: Añade logging a una base de datos
4. **Webhooks**: Notifica cuando un post se crea
5. **Multiple sites**: Soporta múltiples WordPress desde una API

## 📞 Soporte

Si tienes problemas:
1. Revisa los logs en Render Dashboard
2. Verifica las variables de entorno
3. Prueba los endpoints con Postman/Thunder Client primero
4. Verifica que WordPress acepte Basic Auth

---

**¡Listo!** Ahora tienes una API HTTP completa para gestionar WordPress con IA desde n8n o cualquier otra herramienta.
