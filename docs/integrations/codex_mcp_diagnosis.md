# Diagnóstico OAuth Codex → MCP remoto

> **Actualización posterior:** la creación autorizada de `ti-codex` y la
> configuración local se aplicaron después de este diagnóstico. Estado vigente,
> callback observado y pruebas pendientes en
> [`codex_mcp_connection.md`](codex_mcp_connection.md). Lo siguiente conserva
> la evidencia y las decisiones de la fase previa a autorización.

**Fecha:** 11/11/2026, pruebas 08:45–08:55 UTC.  
**Endpoint:** `https://ti-136-114-21-18.sslip.io/mcp`.  
**Estado:** causa reproducida; corrección OAuth propuesta, **pendiente de autorización**.
No se modificaron clientes OAuth, políticas, infraestructura ni configuración
real de Codex. No se afirma una conexión exitosa desde la interfaz del dueño.

## 1. Causa raíz demostrada

La entrada `big_data_ii_-_threat_intelligence` de
`C:\Users\steve\.codex\config.toml` contiene la URL, pero **no un client ID
OAuth predefinido**, secreto, bearer ni headers. Codex no selecciona
automáticamente `ti-chatgpt` por compartir servidor.

La secuencia observada es:

1. `/mcp` devuelve el desafío OAuth esperado, HTTP401.
2. Codex obtiene correctamente discovery del recurso y del authorization server.
3. Al no disponer de client ID y no anunciarse CIMD, intenta DCR.
4. Keycloak rechaza el registro anónimo por la política **Trusted Hosts**.
5. El proceso termina antes del login, callback, canje de código o negociación
   MCP autenticada.

Reproducción real con **Codex CLI 0.139.0**, configuración aislada y
`mcp login ti_diagnosis --scopes ti:read`, exit1:

```text
Error: Registration failed: Dynamic registration failed: Registration failed:
HTTP 403 Forbidden: {"error":"insufficient_scope",
"error_description":"Policy 'Trusted Hosts' rejected request to
client-registration service. Details: Host not trusted."}
```

Este `insufficient_scope` pertenece al **registro de clientes**; no significa
que el JWT de MCP carezca de `ti:read`. No hubo JWT en esa fase.

La política anónima activa exige coincidencia del host solicitante y de las
URI del cliente; no muestra hosts confiables configurados en la allowlist
consultada. Que exista `registration_endpoint` **no garantiza permiso DCR**.
`registrationAllowed=false` es registro de usuarios, no prueba sobre DCR.

## 2. Evidencias y correlación

Rutas relativas a `docs/evidence/codex_diagnosis/`:

| Evidencia | Resultado |
|---|---|
| `local.json` | URL correcta; sin client ID ni credenciales configuradas. No se leyeron almacenes de autenticación. |
| `reproduction.json`, `reproduce.py` | Binario real 0.139.0; DCR403 Trusted Hosts, reproducido dos veces. |
| `server_logs.json` | Caddy: discovery200 y `/mcp`401. Keycloak: REGISTER_ERROR/not_allowed a las08:45:11,08:45:26,08:51:21 y08:51:56. |
| `policies.log`, `policies_probe.py` | Admin API de solo lectura: políticas DCR y eventos CLIENT_REGISTER_ERROR/not_allowed. |
| `http.json`, `http_probe.py` | Nueva pasada de discovery/desafío y callback rechazado, sin login ni tokens. |
| `config_fields.json`, `config_fields_probe.py` | Compatibilidad de campos comprobada con tipos TOML inválidos en configuración aislada. |

Los intentos Caddy con familia de agente `codex` a las08:45 coinciden
temporalmente con errores de registro Keycloak. No se atribuye con certeza
un intento a una ventana concreta del usuario: no se obtuvo el log privado
de esa interfaz. Los intentos propios08:51 sí tienen error y tiempo conocidos.

Caddy omite intencionadamente access logs `/auth/*`: la ausencia de una línea
POST DCR en Caddy no implica que no llegase. El error del cliente y los
eventos Keycloak establecen el rechazo. El sondeo acotó cada servicio a3h y
2500 líneas; no es una auditoría histórica completa.

El filtro de errores de MCP no encontró coincidencias en esa ventana. Eso
es compatible con un fallo anterior al uso autenticado del recurso, pero no
prueba ausencia absoluta de cualquier error de MCP.

## 3. HTTP, discovery y protocolo

| Solicitud nueva | Resultado |
|---|---|
| POST `/mcp` initialize sin bearer | 401, desafío con URL correcta de metadata. |
| GET `/.well-known/oauth-protected-resource/mcp` | 200, resource exacto y scope `ti:read`. |
| GET `/.well-known/oauth-protected-resource` | 404; no bloquea al cliente que sigue el desafío, como ocurrió aquí. |
| GET `/.well-known/oauth-authorization-server/auth/realms/ti` | 200. |
| GET `/auth/realms/ti/.well-known/openid-configuration` | 200. |

Desafío observado:

```text
Bearer error="invalid_token", error_description="Authentication required",
resource_metadata="https://ti-136-114-21-18.sslip.io/.well-known/oauth-protected-resource/mcp"
```

- Issuer exacto: `https://ti-136-114-21-18.sslip.io/auth/realms/ti`.
- Resource/audience exacto: `https://ti-136-114-21-18.sslip.io/mcp`, sin barra final.
- PKCE S256 e identificación del issuer en la respuesta están anunciados.
- CIMD no está anunciado. No basta con añadir un flag si Keycloak no implementa
  el contrato de validación de metadata de clientes.
- La metadata global no enumera `none` como método de autenticación del token
  endpoint. Eso no demuestra que Keycloak rechace todos los clientes públicos;
  se debe probar el cliente nativo propuesto una vez autorizado.

La verificación independiente anterior del mismo día
[`mcp_live.json`](../evidence/integration_setup/mcp_live.json) acreditó
Authorization Code, S256, issuer/audience, refresh post/basic y MCP2025-11-25;
las seis herramientas funcionaron con el SDK, **no con Codex**. No se repitió
ese flujo confidencial en este diagnóstico ni se extrapola a una conexión Codex.

No hay evidencia de que TLS, CORS, Origin, audience o versión MCP causen este
fallo: el cliente llegó a DCR y recibió un rechazo OAuth explícito. El callback,
los tokens y la negociación autenticada aún podrían revelar otros problemas
tras corregir el registro. No se amplió CORS ni se desactivó protección de hosts.

## 4. Por qué no basta con indicar `ti-chatgpt`

El cliente existente es confidencial, requiere secreto, S256 y consentimiento.
Sus callbacks son:

```text
https://chatgpt.com/connector_platform_oauth_redirect
https://chatgpt.com/connector/oauth/*
https://localhost/callback
```

Una solicitud real de autorización con ese client ID, S256,
`scope=openid ti:read`, resource correcto y
`redirect_uri=http://127.0.0.1:43219/callback` devolvió **HTTP400,
Invalid parameter: redirect_uri**, sin redirigir ni pedir credenciales.
HTTPS localhost no equivale a HTTP127.0.0.1 con puerto.

### Versión instalada frente a documentación actual

El launcher npm falló en este shell porque no encuentra Node. Se utilizó
directamente el binario existente:

```text
C:\Users\steve\AppData\Roaming\npm\node_modules\@openai\codex\node_modules\@openai\codex-win32-x64\vendor\x86_64-pc-windows-msvc\bin\codex.exe
```

Su `mcp add --help` ofrece `--oauth-client-id` y `--oauth-resource`, **no
`--oauth-client-secret`**. Las pruebas de parsing detectaron:

| Campo | Codex0.139.0 observado |
|---|---|
| `mcp_servers.<name>.oauth.client_id` | Tipo string validado; CLI lo escribe. |
| `.oauth.client_secret` | Un entero inválido no se rechaza; aparentemente ignorado. No confiar en él. |
| `.oauth.callback_url` / `.oauth.callback_port` | Tipos inválidos no se rechazan; aparentemente ignorados. |
| `mcp_oauth_callback_url` / `mcp_oauth_callback_port` globales | Tipos string/u16 validados. |

La documentación oficial actual sí contempla clientes confidenciales y
callbacks por servidor. **Codex no exige universalmente un cliente público**,
pero no debe recomendarse esa receta nueva como funcional en este binario.
Aceptar TOML sin error no demuestra soporte: puede ignorar claves desconocidas.
No se probó el canje confidencial de esta versión y no se da por compatible.

## 5. Cambio mínimo y seguro propuesto — no aplicado

**Recomendación para conservar el binario actual:** registrar explícitamente
un cliente nativo separado **`ti-codex`**, sin modificar `ti-chatgpt`:

- OpenID Connect; enabled; **publicClient=true**, sin secreto distribuido al escritorio.
- Authorization Code habilitado; **PKCE S256 obligatorio** y consentimiento.
- Implicit, Direct Access Grants/password, service accounts y device flow deshabilitados.
- Scope de aplicación predeterminado solo `ti:read`; `openid` en la solicitud.
  `offline_access` únicamente opcional si se necesita y se valida su política.
- Reutilizar el scope/mapeo de audiencia `ti:read` ya existente para que el
  access token contenga audience MCP y `sub`; no añadir scope administrativo.
- Registrar **solo la URI loopback exacta que emita esta versión**. Puerto
  fijo43219 si está libre; sin wildcard de host o path.
- No habilitar DCR anónimo, no eliminar Trusted Hosts, no cambiar issuer,
  verificador JWT, TTL, seguridad de red ni el cliente de ChatGPT.

Un cliente nativo público con S256 no elimina la autenticación del usuario:
evita tratar un secreto copiable de escritorio como credencial confidencial.
La aprobación debe incluir creación del cliente y edición puntual local.
No requiere recursos cloud adicionales ni reiniciar contenedores.

**Alternativa:** actualizar Codex a una versión que pruebe soporte confidencial
y crear un cliente separado confidencial con callback exacto. No se ha
seleccionado ni instalado tal versión. No pegar secretos en chat, argumentos
de shell ni documentos; la receta oficial de secreto en TOML requiere además
protección del archivo. Convertir `ti-chatgpt` a público queda descartado.

## 6. Reconexión después de autorizar el cambio

1. Guardar copia privada de `config.toml`, sin publicarla, y exportación privada
   de los ajustes del cliente que se vaya a crear. No tocar almacenes de tokens.
2. Crear `ti-codex` con los ajustes de §5. No borrar ni reemplazar `ti-chatgpt`.
3. Modificar **solo** la entrada existente para evitar conectores duplicados:

   ```toml
   [mcp_servers.big_data_ii_-_threat_intelligence]
   url = "https://ti-136-114-21-18.sslip.io/mcp"
   scopes = ["openid", "ti:read"]

   [mcp_servers.big_data_ii_-_threat_intelligence.oauth]
   client_id = "ti-codex"
   ```

   Conservar otras opciones legítimas. No añadir bearer, headers de autorización
   ni secretos. Esto omite DCR, no omite login.
4. Para0.139.0, los ajustes de listener compatibles son **globales**, antes de
   cualquier tabla TOML:

   ```toml
   mcp_oauth_callback_port = 43219
   mcp_oauth_callback_url = "http://127.0.0.1:43219/callback"
   ```

   Revisar primero si afectan otros MCP OAuth. No sobrescribir ajustes globales
   existentes sin acuerdo; si los hay, usar su callback/puerto y registrar ese.
   Este puerto es local, no se abre en el firewall de la VM.
5. En PowerShell usar el binario comprobado mientras el launcher no encuentre Node:

   ```powershell
   $codex = "$env:APPDATA\npm\node_modules\@openai\codex\node_modules\@openai\codex-win32-x64\vendor\x86_64-pc-windows-msvc\bin\codex.exe"
   & $codex mcp login big_data_ii_-_threat_intelligence --scopes openid,ti:read
   ```

6. **Antes de aceptar una URI en Keycloak**, leer localmente el parámetro
   `redirect_uri` de la autorización emitida por ese Codex. Puede añadir un
   sufijo específico del servidor. Registrar esa URI completa y literal en
   `ti-codex`, cancelar el primer intento y repetir el login. No compartir la
   URL de autorización ni el callback completo con code/state. No se inventa
   aquí un sufijo ni se asume que0.139.0 usa el callback estable de la guía nueva.
7. Entrar con la cuenta autorizada y aceptar consentimiento. El login debe
   finalizar en Codex, no solamente en la página de Keycloak.
8. Comprobar `mcp list` y la interfaz MCP; ejecutar
   `get_vulnerability_statistics` y después las seis herramientas de lectura.
   Verificar issuer, audience y scope en memoria; nunca imprimir el JWT.
9. Confirmar ausencia de DCR403, code exchange correcto, S256 obligatorio,
   rechazo de code replay, refresh si aplica y seis herramientas satisfactorias.
   Solo entonces declarar la conexión resuelta. Si falla, conservar únicamente
   timestamp, etapa, HTTP status y etiqueta de error sanitizada.

**Rollback:** restaurar únicamente los cambios locales propios y deshabilitar
el cliente nuevo; no revertir ajustes ajenos ni tocar datos CVE. No se necesita
recrear la VM, modificar DAG, interrumpir ETL ni cambiar respaldos.

## 7. Límites y referencias

- No se creó `ti-codex`, no se abrió DCR y no se aplicó la propuesta.
- No se verificó el éxito E2E del cliente nuevo ni una sesión del dueño.
- Los sondeos de admin API fueron lecturas; las solicitudes de autorización
  negativas y DCR rechazadas dejaron eventos de auditoría, sin crear clientes.
- Se usaron configuraciones de prueba aisladas en
  `%LOCALAPPDATA%\Temp\opencode`; no la configuración/autenticación real.
- [MCP en Codex, documentación oficial](https://developers.openai.com/codex/mcp.md):
  cliente predefinido, DCR/CIMD, callbacks y diferencias de versión.
- [Configuración oficial](https://developers.openai.com/codex/config-file/config-reference/).
- [Guía existente ChatGPT](chatgpt_mcp_setup.md), que no sustituye una receta Codex.

**Conclusión:** no es un MCP sin autenticación ni un problema de bases. Es un
desajuste de registro OAuth: Codex intenta DCR que Keycloak prohíbe; el cliente
ChatGPT tampoco acepta su callback nativo. La corrección propuesta conserva
la autenticación y separa ambos clientes, pendiente de aprobación y prueba final.
