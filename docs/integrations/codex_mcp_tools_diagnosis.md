# Codex App: diagnóstico y corrección de herramientas MCP 0/6

> **Referencia histórica anterior a la expansión de Cassandra.** Las cifras, pruebas y comandos son de su corte original, no instrucciones vigentes para GCP. Para la arquitectura y operación actuales, consultar [el cierre distribuido](../audits/distributed_final_closure.md).

> **Fase funcional posterior:** se ejecutaron las seis herramientas y se
> corrigió la ausencia de Log4Shell y los filtros. Corte vigente174735 CVE,
> fuente real y resultados por función en
> [`codex_mcp_functional_fix.md`](codex_mcp_functional_fix.md).
> Este documento conserva el diagnóstico previo de descubrimiento/OAuth.

**11/11/2026, investigación16:53–17:11 UTC.**

**Resultado técnico:** el ejecutable real que utiliza Codex App descubre
**6/6 herramientas** y ejecuta `get_vulnerability_statistics` con la sesión
OAuth que el dueño había iniciado. **La conversación/interfaz de App sigue
pendiente de reconexión y confirmación del dueño.** No se automatizó otro login.

## 1. Causa demostrada y factores de sesión

La autenticación del dueño sí terminó: los eventos Keycloak registran
UPDATE_PASSWORD y LOGIN seguidos de CODE_TO_TOKEN a las16:45:08 UTC, scope
emitido `openid ti:read`. No era necesario volver a restablecer su contraseña.

Sin embargo, el backend nativo de App intenta preparar/renovar esa sesión con
`openid ti:read offline_access`. El cliente `ti-codex` tenía **cero scopes
opcionales asignados**. La reproducción nativa posterior al login produjo:

```text
OAuth token refresh failed: Server returned error response:
invalid_scope: Invalid scopes: openid ti:read offline_access
```

No es un fallo de permisos CRUD, CORS o de las seis funciones del servidor.
El fallo de preparación OAuth impide completar la conexión que alimenta el
catálogo. El estado nativo era **`authStatus=oAuth`, herramientas0,
serverInfo=null**: credenciales detectadas no equivalen a MCP inicializado.

Además, logs de **Codex Desktop**, no solo del verificador, muestran:

-16:42:09: initialize rechazado por falta de autenticación, antes de terminar
  el login de las16:45.
-16:45:52: `omitting pending optional MCP server` para este servidor durante
  la captura del catálogo de una conversación. Podía quedar fuera del contexto
  inicial mientras arrancaba, porque estaba configurado como opcional.

Se demuestran así un bloqueo OAuth reproducible después del login y una
omisión de catálogo pendiente en App. No se leyó el texto de la conversación
del dueño para atribuir su frase «0/6» a una llamada concreta; no se presenta
una respuesta del modelo como medición fiable del inventario.

## 2. Configuración y CODEX_HOME efectivos

Se inspeccionaron procesos Windows activos con salida allowlist del entorno
y argumentos, sin volcar tokens ni command lines completas:

- App principal: paquete `OpenAI.Codex_26.1106.6628.0_x64__2p2nqsd0c76g0`.
- Su proceso `codex.exe app-server`: PID26468, hijo de App PID16532.
- En ambos, `CODEX_HOME` y `HOME` no estaban definidos y
  `USERPROFILE=C:\Users\steve`. Por tanto usan el home por defecto
  **`C:\Users\steve\.codex`**, no otro CODEX_HOME configurado en su entorno.
- Los overrides del app-server correspondían a `features.code_mode_host` y
  al plugin integrado `codex_app`; no había override de este MCP.
- `config/read`, usando el binario real y el directorio del proyecto, confirmó
  URL, enabled, client ID, scopes y `environment_id=local` efectivos.

**Diferencia de versiones importante:**

| Ejecutable | Versión observada | Resultado |
|---|---|---|
| CLI npm usado en la fase anterior | 0.139.0 | En esta fase no usa satisfactoriamente la sesión almacenada por el runtime nuevo: authStatus unsupported,0 herramientas y AuthRequired. |
| Ejecutable realmente lanzado por App | **0.167.0-alpha.4.1** | Antes de corregir: OAuth presente,0 herramientas; después: OAuth,6 herramientas y llamada real PASS. |

Binario que debe usarse para reproducir esta investigación:

```text
C:\Users\steve\AppData\Local\OpenAI\Codex\bin\9e1da79431da526b\codex.exe
```

No se migró, copió ni editó manualmente el almacén OAuth. Se delegó su uso al
propio binario nativo. No se leyó `auth.json` ni se imprimieron credenciales
de keyring. El `oAuth` nativo, el uso de la sesión guardada y la llamada real
prueban que el runtime de App puede recuperarla correctamente. No prueban
compatibilidad de ese almacén con todas las versiones antiguas del CLI.

## 3. Correcciones aplicadas, estrictamente acotadas

### A. Solo el cliente OAuth `ti-codex`

Se asignó el scope existente **`offline_access` como opcional**, no como
predeterminado. Los scopes predeterminados siguen siendo únicamente `ti:read`.
Esto permite procesar la solicitud de scopes del runtime nuevo.

**No se asignó el rol `offline_access` a `ti-owner` ni a ningún usuario.**
Se conservó la restricción de ese scope al rol `offline_access`, y el dueño
sigue sin ese rol. La corrección no concede por sí sola un nuevo privilegio
de sesión offline al usuario. No se modificaron los tiempos de sesión offline
del realm ni la rotación de refresh tokens.

Se verificaron por lectura antes/después:

- `ti-codex`: mismo PKCE S256, publicClient, consentimiento, fullScopeAllowed,
  callback literal y scopes predeterminados.
- `ti-chatgpt`: misma configuración, scopes y mappers.
- Sin cambios en roles del dueño, role gate del scope ni políticas DCR.
- Ningún cambio de contraseña, infraestructura, motores, CVE o scheduling.

### B. Solo esta entrada local

En `C:\Users\steve\.codex\config.toml` se añadieron:

```toml
[mcp_servers.big_data_ii_-_threat_intelligence]
enabled = true
required = true
startup_timeout_sec = 30
url = "https://ti-136-114-21-18.sslip.io/mcp"
scopes = ["openid", "ti:read"]

[mcp_servers.big_data_ii_-_threat_intelligence.oauth]
client_id = "ti-codex"
```

Los callbacks globales previos permanecen intactos:
puerto43219 y base `http://127.0.0.1:43219/callback`; Keycloak conserva el
callback observado `http://127.0.0.1:43219/callback/GnTeVrGD9Hed`.

`required=true` evita que una conversación nueva omita silenciosamente este
MCP como opcional mientras arranca. Si no puede conectarse, debe mostrar el
fallo; no se omite la autenticación ni se conceden permisos de ejecución extra.
La espera de arranque se acotó a30s. No debe sobreescribirse el archivo con
este ejemplo: **ya está aplicado** y las demás opciones se conservaron.

Copia privada previa:
`C:\Users\steve\.codex\config.pre-tool-discovery-20261111T1705.toml.bak`.
No publicarla; puede contener configuración personal.

## 4. Descubrimiento real: antes y después

Se usó el protocolo JSON-RPC del app-server que publica el propio binario:

1. `initialize` / `initialized` para el cliente diagnóstico.
2. `config/read` para obtener únicamente los campos allowlist del MCP objetivo.
3. `mcpServerStatus/list` con detalle full.
4. `thread/start` efímero, sandbox read-only, **sin turno de modelo**.
5. `mcpServerStatus/list` con el thread ID diagnóstico.
6. `mcpServer/tool/call`, `get_vulnerability_statistics`, argumentos `{}`.

El app-server realiza la conexión MCP real y obtiene el catálogo del endpoint,
usando sus credenciales almacenadas. No es un catálogo simulado ni una llamada
Python al MCP pasando un token preparado por el agente.

| Resultado | Antes | Después,17:07:02 UTC |
|---|---|---|
| Runtime App | 0.167.0-alpha.4.1 | Misma versión |
| OAuth detectado | oAuth | oAuth |
| Herramientas reales | 0 | **6** |
| Información servidor | null | Threat Intelligence NVD,1.30.0 |
| Llamada MCP estadísticas | No disponible | **PASS**,174734 CVE |
| `as_of` del snapshot | — | `2026-11-11T03:01:47.586892+00:00` |

Herramientas devueltas por el catálogo nativo:

1. `search_vulnerabilities`
2. `get_cve_details`
3. `get_top_cwes`
4. `get_vulnerability_statistics`
5. `get_affected_products`
6. `explore_cve_relationships`

**Resources0 y resourceTemplates0 son normales:** este MCP expone herramientas,
no recursos MCP. No inferir «0 herramientas» de `resources/list` vacío. Las
advertencias Method not found del servidor integrado `codex_app` corresponden
a otro MCP y no son una prueba de fallo del de Threat Intelligence.

El diagnóstico lanzó un **proceso separado** con el mismo ejecutable de App.
No inyectó solicitudes en el stdin de App, no controló su GUI y no reemplazó
su conversación. Deshabilitó `node_repl` solo mediante override del proceso
diagnóstico para no arrancarlo; no modificó su archivo ni sus procesos activos.
El hilo diagnóstico fue efímero y no se envió ningún prompt a un modelo.

### Evidencias

Rutas relativas a `docs/evidence/codex_diagnosis/`:

| Archivo | Contenido |
|---|---|
| `app_process.json` | Procesos, ejecutables y entorno allowlist; prueba de home por defecto compartido. |
| `post_login_local_logs.json` | SQLite abierto en modo ro; clasificaciones de errores, sin mensajes auth crudos. |
| `refresh_scope_inspection.log` | Scope opcional ausente, gate de rol y eventos de login/canje exitoso. |
| `native_discovery_app_before_fix.json` | Reproducción de OAuth presente pero0 herramientas. |
| `native_discovery_npm.json` | Diferencia del CLI0.139.0, no presentado como estado de App. |
| `refresh_scope_after.log` | Asignación opcional aplicada, restricciones/roles conservados. |
| `post_fix_invariants.json` | Comparación de clientes, mappers, roles, políticas y demás configuración local. |
| `native_discovery_app.json` | **6/6 y llamada real PASS**, usando ejecutable de App; no GUI. |
| `post_login_server_logs.log`, `post_fix_server_logs.log` | Caddy/Keycloak/MCP sanitizados; discovery y solicitudes MCP, sin headers/query/token. |

Dos fallos del instrumental se conservaron, sin ocultarlos como éxitos:

- El lector inicial de JSON-RPC usó cp1252 en vez de UTF-8 y falló; se corrigió
  el lector, no el servidor (`native_discovery_app_initial_failure.json`).
- El script de asignación sí aplicó el scope, pero su comparación posterior
  incluía la lista de scopes que deliberadamente había cambiado. Falló esa
  aserción; **no se repitió la mutación**. Se verificó por consultas de solo
  lectura y prueba nativa posterior; detalle en
  `refresh_scope_fix_initial_verification_failure.json`.

## 5. Pasos exactos en Codex App

1. Guarda cualquier trabajo abierto. **Cierra Codex App completamente y vuelve
   a abrirla** para que no reutilice el catálogo/configuración de la sesión
   anterior. El agente no terminó sus procesos por ti.
2. Selecciona el proyecto Big Data II en el **host local de este Windows**,
   no una conversación ejecutada exclusivamente en un host remoto.
3. En los ajustes MCP, confirma que sigue habilitada la entrada existente
   `big_data_ii_-_threat_intelligence`. No crear otra entrada ni pegar bearer
   tokens/client secrets. No cerrar sesión OAuth por rutina: la sesión guardada
   ya funcionó en el runtime nativo comprobado.
4. **Crea una conversación nueva** después de que el MCP termine de iniciar.
   No uses la respuesta «0/6» de la conversación anterior como prueba actual.
5. Envía:

   ```text
   Busca las herramientas del MCP big_data_ii_-_threat_intelligence.
   Lista los seis nombres del catálogo y ejecuta realmente
   get_vulnerability_statistics con argumentos {}.
   Muestra total_cves y as_of e identifica la llamada a la herramienta.
   ```

6. Confirma que hay una llamada real de herramienta en App y comparte solo
   nombres/resultados públicos o el error sanitizado con su hora. Entonces
   puede cerrarse la comprobación E2E de App.

Si App vuelve a pedir Autenticarse, completa tú el flujo y el consentimiento;
no uses una contraseña temporal anterior después de haberla cambiado. Si
continúa fallando, no repitas login en bucle: con `required=true` debe existir
un error de arranque concreto que investigar.

### Reproducir sin GUI

Desde la raíz del proyecto:

```powershell
.\.venv\Scripts\python.exe docs\evidence\codex_diagnosis\discover_native_tools.py --binary app --call-readonly-stats
```

La ruta del binario está fijada al build comprobado; revisarla si App se actualiza.
El comando no inicia login ni muestra tokens; puede renovar la sesión mediante
el runtime nativo. No ejecutar varias renovaciones diagnósticas en paralelo.

## 6. Rollback y límites de cierre

Rollback de **esta fase solamente**, si se solicita:

- Retirar únicamente `required=true` y `startup_timeout_sec=30` de esta entrada.
  Comparar con la copia privada; no restaurar todo el archivo si hay cambios
  posteriores del dueño.
- Mediante Admin API privada, localizar IDs de `ti-codex` y `offline_access` y
  ejecutar DELETE `/auth/admin/realms/ti/clients/{client-id}/optional-client-scopes/{scope-id}`.
  No borrar el scope compartido, no modificar `ti-chatgpt` ni roles de usuario.
- Advertencia: retirar esa asignación puede reproducir el fallo de refresh del
  runtime actual. No se ha ejecutado rollback.

**Cierre:** descubrimiento real y llamada mediante el binario nativo **PASS**.
La GUI y la conversación nueva de **Codex App permanecen PENDIENTES** hasta
confirmación del dueño. No se afirma haber ejecutado las seis herramientas
desde su interfaz ni se presenta la prueba CLI como sustituto de esa evidencia.
