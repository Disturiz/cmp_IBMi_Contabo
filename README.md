# MCP IBM i VENTAPF para ChatGPT Desktop / ChatGPT Apps

Proyecto base para exponer una tabla `VENTAPF` alojada en IBM i `pub400.com` como un **servidor MCP remoto de solo lectura**, de modo que ChatGPT pueda consultarla desde una app MCP.

## Qué hace este proyecto

Expone estas herramientas MCP:

- `ping_ibmi`: valida conectividad con IBM i.
- `obtener_columnas`: lista las columnas detectadas en la tabla.
- `ver_muestras`: devuelve algunas filas de muestra.
- `total_registros`: cuenta registros.
- `ventas_por_filtros`: consulta filas filtrando por cliente y/o producto.
- `top_productos`: agrupa y cuenta por producto.

## Arquitectura

```text
ChatGPT / ChatGPT Desktop
        ↓
   App MCP (Developer mode)
        ↓
Servidor MCP remoto (Python + FastMCP)
        ↓
JDBC (JayDeBeApi + jt400.jar)
        ↓
IBM i PUB400 → LIBRERÍA/TABLA VENTAPF
```

## Requisitos

1. Python 3.11 o superior.
2. Acceso a `pub400.com`.
3. Usuario con permisos de lectura sobre la librería y tabla.
4. `jt400.jar` disponible en `./drivers/jt400.jar`.
5. Un servidor público HTTPS para publicar el MCP remoto.

## 1) Preparar entorno

```bash
python -m venv .venv
```

### Windows PowerShell

```powershell
.\.venv\Scripts\Activate.ps1
```

### Linux / macOS

```bash
source .venv/bin/activate
```

Instala dependencias:

```bash
pip install -r requirements.txt
```

## 2) Preparar configuración

Copia el archivo de ejemplo:

### Windows

```powershell
copy .env.example .env
```

### Linux / macOS

```bash
cp .env.example .env
```

Edita `.env` y ajusta como mínimo:

- `IBMI_USER`
- `IBMI_PASSWORD`
- `IBMI_LIBRARY`
- `IBMI_TABLE`
- `IBMI_CLIENT_COLUMN`
- `IBMI_PRODUCT_COLUMN`
- `JT400_JAR`

## 3) Estructura sugerida

```text
mcp_ibmi_ventapf/
├─ main.py
├─ db.py
├─ tools.py
├─ .env.example
├─ requirements.txt
├─ README.md
└─ drivers/
   └─ jt400.jar
```

## 4) Ejecutar localmente

```bash
python main.py
```

Por defecto el servidor levantará en:

```text
http://localhost:8000
```

Con `MCP_TRANSPORT=sse`, la URL pública que normalmente usarás en ChatGPT será similar a:

```text
https://tu-dominio.com/sse/
```

## 5) Probar antes de publicar

Primero confirma que la conectividad a IBM i funcione con el inspector MCP o con tu cliente MCP de preferencia.

Puedes empezar llamando estas herramientas en este orden:

1. `ping_ibmi`
2. `obtener_columnas`
3. `ver_muestras`
4. `ventas_por_filtros`
5. `top_productos`

## 6) Publicar como MCP remoto

Debes desplegarlo en un host accesible por Internet con HTTPS. Lo habitual es usar:

- Render
- Railway
- Replit
- VPS con Nginx
- Azure / AWS / GCP

### Recomendaciones de despliegue

- Usa **solo lectura**.
- No expongas credenciales en el código.
- Mantén `jt400.jar` en una ruta conocida.
- Restringe el firewall si tu infraestructura lo permite.
- Agrega logs y rotación.
- Considera OAuth o una capa de autenticación delante del MCP para entornos reales.

## 7) Conectar en ChatGPT

Según la documentación actual de OpenAI, las apps MCP personalizadas se crean en **Developer mode**, proporcionando el **endpoint** y los **metadatos requeridos** del servidor MCP, y luego eligiendo el mecanismo de autenticación. Las apps se crean desde **Settings → Apps → Create** o desde **Workspace settings → Apps → Create**, según el plan. Además, los **remote MCP servers** se conectan por Internet y el Apps SDK es la vía recomendada para conectarlos a ChatGPT. citeturn415707view0turn415707view1

### Pasos prácticos

1. Abre ChatGPT.
2. Activa **Developer mode** si tu plan y permisos lo permiten.
3. Ve a **Settings → Apps → Create**.
4. Ingresa la URL pública de tu servidor MCP.
5. Completa nombre, descripción y autenticación.
6. Guarda la app.
7. Prueba consultas como:
   - "Valida conexión con IBM i"
   - "Muéstrame las columnas de VENTAPF"
   - "Dame 10 ventas del cliente CARLOS"
   - "Top 5 productos"

## Ejemplo de datos a registrar en ChatGPT

Este proyecto incluye un archivo `mcp_chatgpt_config_example.json` con valores de referencia para llenar el formulario de creación de la app.

## Seguridad

### Lo recomendable

- usuario de solo lectura
- límites máximos en las consultas
- no permitir SQL libre
- validar nombres de columnas
- monitorear logs

### Lo que este proyecto evita intencionalmente

- `INSERT`
- `UPDATE`
- `DELETE`
- ejecución libre de SQL enviada por el modelo

## Notas importantes

1. **Ajusta nombres de columnas**: `CLIENTE` y `PRODUCTO` son valores por defecto; cambia `.env` si tu tabla usa otros nombres.
2. **Ajusta nombre de biblioteca**: en PUB400 el esquema real debe existir y tu usuario debe tener permiso.
3. **Ajusta ordenamiento**: si quieres ordenar por fecha o número de documento, define `IBMI_DEFAULT_ORDER_COLUMN` en `.env`.
4. **Endpoint exacto**: según tu despliegue, la URL final puede terminar en `/sse/`. Verifica la ruta expuesta por el transporte que publique tu servidor. OpenAI muestra ejemplos conectando servidores MCP remotos por URL pública y usando SSE en sus ejemplos/documentación. citeturn517221view0turn415707view1

## Ejemplos de preguntas útiles en ChatGPT

- "Ejecuta ping_ibmi"
- "Lista las columnas de la tabla"
- "Muéstrame 5 registros de muestra"
- "Busca ventas del cliente DOUGLAS"
- "Dame top 10 productos"

## Próximas mejoras sugeridas

- agregar autenticación OAuth
- agregar herramienta de resumen por cliente
- agregar filtros por fecha
- agregar tool de metadata de tabla
- agregar caché de columnas para validación más fuerte
- agregar compatibilidad `search/fetch` si después quieres usarlo también con flujos de investigación sobre documentos/datos indexados
