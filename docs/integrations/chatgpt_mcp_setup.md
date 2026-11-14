# Conectar ChatGPT al MCP — Big Data II / Threat Intelligence

**Verificado en producción: 11/11/2026, 07:13–07:20 UTC.**
Endpoint: **https://ti-136-114-21-18.sslip.io/mcp**.

## 1. Qué está listo y qué falta

| Aspecto | Resultado comprobado |
|---|---|
| Transporte | MCP **Streamable HTTP**, JSON-RPC 2.0, servidor stateless, respuestas JSON; no es el antiguo transporte HTTP+SSE con endpoint `/sse`. |
| Runtime | SDK Python `mcp` **1.30.0**, FastMCP incluido en ese SDK, Uvicorn0.54.0, PyJWT2.15.1; Keycloak26.8.2. No confundir con el paquete independiente `fastmcp`. |
| Negociación nueva | `initialize` respondió `protocolVersion: "2025-11-25"`, servidor `Threat Intelligence NVD`, versión1.30.0. |
| Versiones admitidas por el SDK desplegado | `2024-11-05`, `2025-03-26`, `2025-06-18`, `2025-11-25`. No se afirma soporte de una versión posterior. |
| OAuth | Authorization Code + PKCE S256, cliente confidencial predefinido, consentimiento y JWT firmado; probado con login real de la identidad de prueba del dueño. |
| Renovación | Refresh token emitido; renovación200 con `client_secret_post` y con `client_secret_basic`; herramientas ejecutadas con el token renovado. |
| Herramientas | `tools/list`: seis herramientas; las seis ejecutadas sin error. Código OAuth reutilizado e identificador inválido rechazados. |
| Cuenta ChatGPT | **PENDIENTE: no se inició sesión ni se vinculó la cuenta ChatGPT del dueño.** Estas pruebas usan un cliente MCP de verificación, no ChatGPT. |

El transporte, discovery y flujo de cliente predefinido satisfacen los
prerrequisitos documentados por OpenAI. **Compatibilidad final con tu cuenta,
workspace e interfaz concreta de ChatGPT: pendiente de los pasos manuales**.
No equivale a certificación de conformidad completa OAuth2.1 ni a publicación
aprobada en un directorio de OpenAI.

## 2. Valores exactos para el formulario

| Campo | Valor |
|---|---|
| Nombre sugerido | `Big Data II – Threat Intelligence` |
| Descripción sugerida | `Consultas de solo lectura sobre vulnerabilidades NIST NVD en MongoDB, Cassandra y Neo4j.` |
| MCP server URL | `https://ti-136-114-21-18.sslip.io/mcp` **sin barra final** |
| Transporte, si se pregunta | `Streamable HTTP` |
| Autenticación | `OAuth` / OAuth2 Authorization Code con PKCE |
| Método de registro | **Cliente OAuth predefinido/manual**; no exigir registro dinámico para este procedimiento. |
| OAuth Client ID | `ti-chatgpt` |
| OAuth Client Secret | Valor privado de `mcp-oauth-client-secret`; ubicación verificada en §3. **No aparece en este documento.** |
| Scope MCP requerido | `ti:read` |
| Scopes del flujo OIDC probado | `openid ti:read`, separados por espacio |
| PKCE | `S256`, obligatorio en este cliente |
| Resource / audience | `https://ti-136-114-21-18.sslip.io/mcp` |
| Emisor / issuer | `https://ti-136-114-21-18.sslip.io/auth/realms/ti` |
| Token endpoint auth | `client_secret_post` y `client_secret_basic` probados. No elegir `none` para este cliente confidencial. |
| Usuario al abrir Keycloak | `ti-owner` |
| Contraseña del usuario | Valor privado de `keycloak-user-password`; §3. **No es la contraseña de ChatGPT/Google ni la de Basic Auth.** |

No uses `ti-demo` como usuario OAuth: ese usuario solo protege dashboard/API.
No pegues access tokens, refresh tokens, contraseñas ni secretos en el chat,
instrucciones del modelo, archivos Markdown, URL o parámetros de herramientas.

### Endpoints públicos exactos

| Función | URL |
|---|---|
| Metadata del recurso protegido | `https://ti-136-114-21-18.sslip.io/.well-known/oauth-protected-resource/mcp` |
| Discovery OAuth, con ruta de issuer RFC8414 | `https://ti-136-114-21-18.sslip.io/.well-known/oauth-authorization-server/auth/realms/ti` |
| Discovery OIDC alternativo | `https://ti-136-114-21-18.sslip.io/auth/realms/ti/.well-known/openid-configuration` |
| Autorización | `https://ti-136-114-21-18.sslip.io/auth/realms/ti/protocol/openid-connect/auth` |
| Token y refresh | `https://ti-136-114-21-18.sslip.io/auth/realms/ti/protocol/openid-connect/token` |
| JWKS | `https://ti-136-114-21-18.sslip.io/auth/realms/ti/protocol/openid-connect/certs` |
| UserInfo anunciado | `https://ti-136-114-21-18.sslip.io/auth/realms/ti/protocol/openid-connect/userinfo` |
| Registro dinámico anunciado | `https://ti-136-114-21-18.sslip.io/auth/realms/ti/clients-registrations/openid-connect` |

**UserInfo y DCR se identificaron en metadata; no se ejecutó un alta DCR ni
se probó UserInfo.** No crear clientes adicionales ni modificar el realm para
seguir la ruta manual ya verificada.

## 3. Dónde obtener los dos valores privados

Proyecto GCP: `proyectobigdata2-514216`. VM: `ti-dev-data`, zona `us-central1-a`.

| Uso | Archivo privado de la VM | Referencia Secret Manager verificada |
|---|---|---|
| Secreto del cliente | `/opt/threat-intelligence/secrets/mcp-oauth-client-secret` | Recurso `ti-dev-runtime-bootstrap`, clave JSON `mcp-oauth-client-secret` |
| Login `ti-owner` | `/opt/threat-intelligence/secrets/keycloak-user-password` | Recurso `ti-dev-runtime-bootstrap`, clave JSON `keycloak-user-password` |

Referencia completa:
`projects/proyectobigdata2-514216/secrets/ti-dev-runtime-bootstrap/versions/latest`.

Se comprobó **en memoria**, sin imprimir los valores, que ambas claves existen
en ese payload y coinciden con los archivos usados en producción
(`secret_reference.json`). No hay que buscar un recurso independiente llamado
`mcp-oauth-client-secret`: ese es el nombre del archivo/clave del bootstrap.
El recurso `ti-dev-mcp-token` no es el client secret de este flujo.

Obtén estos valores mediante el gestor privado del operador, la consola
privada de Secret Manager con permiso `secretmanager.versions.access`, o el
canal administrativo IAP existente. Introduce el primero únicamente en el
campo secreto OAuth de ChatGPT y el segundo únicamente en el formulario
Keycloak. No publiques salidas de `cat`, comandos de acceso a secretos,
capturas del payload ni historial de portapapeles. No se descargaron claves
de servicio JSON ni se rotaron credenciales para esta documentación.

## 4. Redirect URIs: qué está registrado y qué copiar

Inspección nueva de la configuración persistente de `ti-chatgpt`:

```text
https://chatgpt.com/connector_platform_oauth_redirect
https://chatgpt.com/connector/oauth/*
https://localhost/callback
```

- **Stable callback**: `https://chatgpt.com/connector_platform_oauth_redirect`.
  Está registrado. El issuer anuncia
  `authorization_response_iss_parameter_supported: true` y la autorización
  probada devolvió `iss` exactamente igual al issuer, requisito que OpenAI
  documenta para usar este callback estable.
- **Callback específico**: si ChatGPT muestra
  `https://chatgpt.com/connector/oauth/{callback_id}`, copia el valor literal
  que muestre tu conexión. `{callback_id}` no es un ID conocido de este proyecto
  ni un valor que debas escribir. El patrón existente cubre esa ruta.
- `https://localhost/callback` se usó únicamente en el verificador automatizado,
  que intercepta el redirect; **no es el callback de ChatGPT ni exige abrir
  un servidor local para conectar ChatGPT**.

La documentación oficial pide copiar la URI exacta que muestra la página de
gestión del MCP. Si tu interfaz muestra otro host/ruta no cubierto, falta
autorizar esa URI exacta mediante el operador del realm. No añadir comodines
globales ni desactivar PKCE. Como endurecimiento futuro, el operador puede
sustituir el patrón por el callback específico después de conocerlo; no se
modificó la configuración funcional durante esta verificación.

## 5. Pasos en ChatGPT

La ruta actual documentada por OpenAI es **ChatGPT Plugins → Add custom MCP
server**; cuentas con la interfaz anterior pueden mostrar Apps/Conectores y
modo desarrollador. No se inspeccionó la UI privada de tu cuenta; los permisos
de workspace/plan y los rótulos concretos son una condición externa.

1. Inicia sesión como dueño en ChatGPT web. Abre
   **https://chatgpt.com/plugins** y selecciona **+ → Add custom MCP server**.
   Si tu cuenta usa Apps/Conectores, busca la opción equivalente de creación
   de MCP personalizado; el administrador debe permitirla si está restringida.
2. Introduce nombre, descripción y URL exactos de §2. Para conexión elige
   **endpoint HTTPS público**, no Tunnel, stdio, SSE antiguo ni servidor local.
3. Selecciona **OAuth**. Si existe selector de registro, usa
   **predefined/manual OAuth client** e introduce `ti-chatgpt` y su secreto.
   No dejes el ID vacío esperando que este procedimiento pruebe DCR.
4. Si se muestran campos de scopes, solicita `openid ti:read`. El permiso
   requerido por el MCP es `ti:read`; `openid` identifica el flujo OIDC.
   No solicitar `kc-admin-api`, que aparece en metadata del realm pero no
   corresponde al permiso de lectura del MCP. `offline_access` es opcional
   y no se necesita para el refresh normal probado.
5. Permite discovery automático. Solo si la UI pide endpoints manuales,
   utiliza autorización/token/issuer de §2; no reemplazar el issuer por `/mcp`.
   Verifica el callback que muestra ChatGPT contra §4.
6. Revisa el aviso de riesgo, acepta **I understand and want to continue**
   y crea la conexión/plugin. La secuencia del formulario puede abrir el
   login antes o después de crearla.
7. En la pestaña Keycloak, inicia sesión con `ti-owner` y la contraseña privada
   correspondiente. Verifica el dominio `ti-136-114-21-18.sslip.io`, realm `ti`.
   Acepta únicamente el consentimiento esperado de lectura NVD.
8. Regresa a ChatGPT y comprueba que se descubran **exactamente las seis
   herramientas de §7**. Instala/habilita la conexión si la UI lo solicita.
9. Abre una conversación nueva, selecciona el plugin/MCP con `@` o mediante
   la selección de herramientas de tu interfaz y ejecuta los ejemplos de §7.
10. Guarda evidencia **sin secretos** de nombre de conexión, herramienta,
    argumentos, resultado y fecha. Solo entonces puede cambiarse la condición
    `chatgpt_account_connected` a verificada en un nuevo reporte.

No es necesario publicar en un directorio público, comprar un dominio,
reconfigurar OAuth ni recrear la VM para intentar la conexión manual.
Si tu superficie solo admite DCR o CIMD y no acepta ID/secret predefinidos,
detente: esa vía **no está verificada** y requiere una decisión/configuración
adicional del operador, no una URL o credencial inventada.

## 6. Discovery y seguridad observados

Respuesta real resumida de la metadata del recurso:

```json
{
  "resource": "https://ti-136-114-21-18.sslip.io/mcp",
  "authorization_servers": ["https://ti-136-114-21-18.sslip.io/auth/realms/ti"],
  "scopes_supported": ["ti:read"]
}
```

Un `POST /mcp` sin bearer obtuvo401 y este challenge real:

```http
WWW-Authenticate: Bearer error="invalid_token", error_description="Authentication required", resource_metadata="https://ti-136-114-21-18.sslip.io/.well-known/oauth-protected-resource/mcp"
```

La raíz `/.well-known/oauth-protected-resource` devuelve404, pero el challenge
publica la URL con `/mcp`, que devuelve200. No confundir ese404 con ausencia
de OAuth. Discovery RFC8414 con ruta de issuer y discovery OIDC:200; JWKS:200.

El cliente es confidencial (`publicClient=false`, `client-secret`), habilitado,
con standard flow y consentimiento; implicit, password grant y service
accounts deshabilitados. El scope default es `ti:read`, el opcional
`offline_access`; un mapper de cliente aporta `sub` y el scope aporta
audiencia literal `/mcp`. JWT requiere `exp`, `iat`, `sub`, `iss`, `aud`,
firma RS256/JWKS, `ti:read` y leeway10s. Access token:600s; refresh rotation
activada y máximo de reutilización0.

La metadata global anuncia PKCE `plain` y `S256`, pero **el cliente concreto
exige S256**. La metadata anuncia registro DCR; su autorización/políticas no
se validaron creando clientes. No anuncia `client_id_metadata_document_supported`:
no se afirma implementación CIMD. `registrationAllowed=false` corresponde
al autorregistro de usuarios, no demuestra que DCR esté bloqueado.

Las herramientas usan autenticación del servidor y anotaciones read-only;
no anuncian `securitySchemes` particulares de OpenAI ni perfil multi-cuenta.
No se necesita inventar una séptima herramienta para la conexión básica.
Funciones avanzadas de reautorización a nivel de herramienta, publicación,
multi-cuenta o restricciones Enterprise por dominio no fueron verificadas.

## 7. Las seis herramientas: contrato y ejemplos

Todas tienen `readOnlyHint=true`, `destructiveHint=false`, `openWorldHint=false`.
No aceptan SQL, Cypher, URL arbitraria, tokens ni credenciales. Identificadores:
`^CVE-\d{4}-\d{4,19}$`; `page`:1–10000; `page_size`:1–100.

| Herramienta | Parámetros exactos | Ejemplo de argumentos JSON | Qué devuelve |
|---|---|---|---|
| `search_vulnerabilities` | `cve_id`:string/null opcional, default null; `page`:int default1; `page_size`:int default25 | `{"page":1,"page_size":5}` | `items`, `total`, `page`, `page_size`; búsqueda por ID exacto si se proporciona. |
| `get_cve_details` | `cve_id`:string obligatorio | `{"cve_id":"CVE-2020-9709"}` | Documento canónico y `raw_cve` de MongoDB;404 si no existe. |
| `get_top_cwes` | Ninguno | `{}` | `items`:top20 CWE del snapshot, no incidentes. |
| `get_vulnerability_statistics` | Ninguno | `{}` | Total, severidad, porcentajes, meses, medias CVSS por versión, productos, `as_of` y resumen del grafo. |
| `get_affected_products` | Ninguno | `{}` | `items`:top20 identidades únicas parte/vendor/product; no todos los productos de un CVE ni un inventario de activos. |
| `explore_cve_relationships` | `cve_id`:string obligatorio | `{"cve_id":"CVE-2020-9709"}` | `items` y `limit:250`: relaciones salientes, etiquetas y propiedades de entidades. |

Prompts de aceptación para una conversación con el MCP habilitado:

1. «Usa `get_vulnerability_statistics` y dime el total y la fecha `as_of`.»
2. «Lista cinco CVE usando `search_vulnerabilities` con page1 y page_size5.»
3. «Consulta `get_cve_details` para CVE-2020-9709; separa fecha de publicación,
   CVSS y CWE. No interpretes el año del ID como año publicado.»
4. «Obtén `get_top_cwes` y explica qué representa su conteo.»
5. «Obtén `get_affected_products`; distingue productos de versiones CPE.»
6. «Explora las relaciones de CVE-2020-9709 y distingue asociación de explotación.»

Prueba real nueva: las seis llamadas dieron PASS. Ejemplo existente:
CVE-2020-9709, publicado2026-11-05, HIGH, CVSS3.1=8.8 y CWE-269.
Su lista de productos está vacía; no completarla por intuición. Estadísticas:
174734 CVE, `as_of=2026-11-11T03:01:47.586892+00:00`.
Los prompts son instrucciones propuestas para el dueño; **no se afirma que
ChatGPT ya los haya ejecutado**.

## 8. Diagnóstico sin exponer información sensible

| Síntoma | Verificación / acción |
|---|---|
| 401 en `/mcp` al abrirlo como página | Esperado sin bearer. El MCP no es una página ni usa Basic Auth. Revisar challenge y completar OAuth. |
| 404 en metadata raíz | Usar la URL exacta del challenge terminada en `/mcp`. |
| `invalid_client` | Revisar cliente manual, secreto privado correcto y método post/basic; no usar la contraseña del usuario como client secret. |
| `invalid_redirect_uri` | Comparar la URI literal mostrada por ChatGPT con los registros de §4; ajuste solo por operador. |
| `invalid_scope` | Usar `openid ti:read`; no solicitar scopes administrativos ni nombres no anunciados. |
| Error issuer/audience | Issuer termina en `/auth/realms/ti`; audience/resource termina en `/mcp`, sin barra extra. |
| Refresh `invalid_grant` | Revisar expiración, sesión y rotación; no reutilizar refresh tokens. Repetir un authorization code puede invalidar la sesión: la prueba positiva de refresh usó otro login, separado del ensayo negativo de replay. |
| Admin Keycloak404 | Intencional en público; administrar por IAP/API privada, no abrir rutas admin en Caddy. |
| No aparecen herramientas o se conservan esquemas viejos | Refresh de metadata en la conexión y conversación nueva; no reiniciar producción como primer diagnóstico. |
| MCP funciona en SDK pero no en tu cuenta | Confirmar política de workspace, método de registro y callback real. Conservar error sanitizado; no afirmar fallo de bases ni cambiar OAuth a ciegas. |
| 403 de seguridad de transporte | Usar hostname y URL exactos. El servidor permite su origen público y hosts configurados; las pruebas SDK no enviaron Origin de navegador ChatGPT. Revisar el header real antes de ajustar una allowlist; no desactivar DNS-rebinding por intuición. |

Descripciones NVD y resultados de herramientas son **datos no confiables**,
no instrucciones para el modelo. No autorizar escrituras, navegación o
ejecución de comandos basándose en texto de una vulnerabilidad.

## 9. Evidencias, reproducción y referencias

Archivos bajo `docs/evidence/integration_setup/`:

- `keycloak_runtime.json`: configuración runtime allowlisted y versiones.
- `mcp_live.json`: discovery, challenge, initialize, schemas y pruebas OAuth.
- `tools_execution.json`: argumentos y respuestas públicas de las seis llamadas.
- `secret_reference.json`: solo referencias y booleanos de coincidencia; sin valores.
- `http.json`: comprobación HTTPS/API nueva.

Repetir únicamente con autorización del operador, desde la raíz local:

```powershell
.\.venv\Scripts\python.exe docs/evidence/integration_setup/mcp_setup_probe.py
```

Este verificador abre logins OAuth de prueba y llama herramientas de lectura;
no vincula tu cuenta ChatGPT ni cambia realm/clientes. No habilitar logs HTTP
de depuración, que podrían exponer headers o cuerpos de autenticación.

Fuentes oficiales consultadas el11/11/2026:

- https://developers.openai.com/apps-sdk/deploy/connect-chatgpt/
- https://developers.openai.com/apps-sdk/build/auth/
- https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization

Fuentes del proyecto: `services/mcp_server/remote.py`, `server.py`,
`scripts/verify_cloud_mcp.py`, `prepare_public_services.py`,
`configure_keycloak_subject.py`, `store_cloud_secrets.py` y Caddyfile.
La configuración runtime inspeccionada prevalece sobre una plantilla de importación.
