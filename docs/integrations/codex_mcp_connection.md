# Codex App → MCP: configuración aplicada y conexión

> **Actualización posterior al login del dueño:** el runtime real de App es
> 0.167.0-alpha.4.1. Se corrigió el scope opcional requerido al renovar y se
> verificaron6/6 herramientas con su binario. Configuración y pasos vigentes en
> [`codex_mcp_tools_diagnosis.md`](codex_mcp_tools_diagnosis.md).
> Este documento conserva el corte anterior y sus pendientes de esa fecha/hora.

**11/11/2026, 09:03–09:11 UTC.**

| Estado | Resultado |
|---|---|
| Cliente Keycloak y configuración local | **APLICADOS** |
| Preflight sin credenciales | **11 comprobaciones PASS** |
| Pruebas unitarias MCP/OIDC | **10 PASS** |
| Validación técnica completa con tokens de `ti-codex` | **PENDIENTE: login y consentimiento manuales** |
| Conexión E2E desde Codex App | **PENDIENTE de confirmación del dueño** |

**No se declara PASS técnico global.** No se automatizaron las credenciales
del dueño ni se reutilizó la contraseña de pruebas anteriores. No se leyó el
almacén de autenticación de Codex. La intervención necesaria se explica en §4.

## 1. Configuración final aplicada

### Keycloak

Se creó un cliente independiente **`ti-codex`** en el realm `ti`:

- OIDC público nativo, sin secreto de cliente distribuido al escritorio.
- Authorization Code habilitado; **PKCE S256 obligatorio** y consentimiento.
- Scope predeterminado exclusivo `ti:read`; sin scopes opcionales asignados.
  La petición incluye `openid ti:read`. No requiere `offline_access` para
  probar refresh normal de la sesión.
- Mapeo de audiencia MCP heredado del client scope `ti:read` y mapper de
  sujeto propio, equivalente al utilizado por el cliente existente.
- Implicit, password grant, service accounts y device flow deshabilitados.
- `fullScopeAllowed=false`; `webOrigins=[]`, sin CORS comodín.
- Un único redirect URI literal:

  ```text
  http://127.0.0.1:43219/callback/GnTeVrGD9Hed
  ```

- TTL access token heredado600s; refresh rotation activa y maxreuse0.

Valores públicos:

| Parámetro | Valor |
|---|---|
| MCP / resource / audience | `https://ti-136-114-21-18.sslip.io/mcp` |
| Issuer | `https://ti-136-114-21-18.sslip.io/auth/realms/ti` |
| Authorization endpoint | `https://ti-136-114-21-18.sslip.io/auth/realms/ti/protocol/openid-connect/auth` |
| Token endpoint | `https://ti-136-114-21-18.sslip.io/auth/realms/ti/protocol/openid-connect/token` |
| Client ID | `ti-codex` |
| Client secret | **No se utiliza**: cliente nativo público con PKCE |

Se compararon antes/después las representaciones y asignaciones de scopes de
`ti-chatgpt`, y las políticas DCR: **sin cambios**. No se habilitó DCR anónimo,
no se recrearon servicios/infraestructura y no se modificaron datos CVE.
El cliente se creó por Admin API privada, usando la credencial administrativa
solo dentro del proceso remoto; no aparece en las evidencias.

### Codex local

Archivo aplicado: `C:\Users\steve\.codex\config.toml`.
Los ajustes globales están antes de las tablas TOML:

```toml
mcp_oauth_callback_port = 43219
mcp_oauth_callback_url = "http://127.0.0.1:43219/callback"

# Las demás opciones y servidores se conservaron.
[mcp_servers.big_data_ii_-_threat_intelligence]
enabled = true
url = "https://ti-136-114-21-18.sslip.io/mcp"
scopes = ["openid", "ti:read"]

[mcp_servers.big_data_ii_-_threat_intelligence.oauth]
client_id = "ti-codex"
```

No pegar el bloque completo sobre el archivo: **ya está aplicado**. No añadir
otro conector, token ni headers. La comparación TOML confirmó que solo cambió
este servidor y los dos ajustes globales nuevos. El otro servidor existente
no tenía client ID OAuth configurado. No había ajustes globales previos de
callback que sobrescribir.

Copia privada previa, fuera del proyecto:
`C:\Users\steve\.codex\config.pre-ti-codex-20261111T0904.toml.bak`.
Contiene configuración personal: no publicarla ni adjuntarla al chat.

## 2. Compatibilidad comprobada con Codex0.139.0

Se ejecutó el binario instalado, no un cliente que imitase su callback:

```text
C:\Users\steve\AppData\Roaming\npm\node_modules\@openai\codex\node_modules\@openai\codex-win32-x64\vendor\x86_64-pc-windows-msvc\bin\codex.exe
```

Primero se observó su solicitud OAuth con configuración aislada. Después se
repitió `mcp login` usando **el archivo real ya editado**. En ambos casos:

- client ID `ti-codex`; response type `code`; PKCE `S256` y state presentes.
- scope `openid ti:read`; resource exacto del MCP.
- Callback exacto `http://127.0.0.1:43219/callback/GnTeVrGD9Hed`.
- Llegó a construir autorización sin DCR. La sesión CLI se canceló antes de
  login; no dejó un listener activo para competir con Codex App.

La URL de autorización completa no se guardó: contenía state/challenge.
La prueba no controló ningún navegador ni introdujo credenciales. El binario
puede abrir el navegador predeterminado, pero el resultado se obtuvo de su
salida de proceso, sin depender de su interfaz gráfica.

El sufijo **lo añadió el binario real** a la URL global base. No añadir ese
sufijo a la configuración global: podría acabar duplicado. Es específico de
la URL del MCP y debe volver a comprobarse si cambia el endpoint o la versión.
El puerto y la URL globales son necesarios en esta versión: los campos nuevos
`.oauth.callback_url`, `.oauth.callback_port` y `.oauth.client_secret` no
demostraron soporte en el diagnóstico anterior.

La versión del backend que usa Codex App no se inspeccionó dentro de su GUI.
Si App utiliza otro host/CODEX_HOME o una versión distinta, debe verificar su
callback antes de ampliar la allowlist. No asumir que la documentación más
nueva describe exactamente0.139.0.

## 3. Validación y evidencias

Directorio: `docs/evidence/codex_diagnosis/`.
Resumen de cierre parcial: `connection_status.json`; el puerto43219 quedó
liberado y la validación técnica global permanece pendiente.

| Prueba | Resultado | Evidencia |
|---|---|---|
| Cliente nativo, scopes, sujeto y audiencia configurados | PASS de configuración, no de emisión | `client_creation.log` |
| Cliente ChatGPT, sus scopes y políticas DCR sin cambios | PASS | `client_creation.log` |
| Callback observado en Codex instalado | PASS | `native_callback.json` |
| Callback observado con configuración real | PASS | `effective_native_callback.json` |
| TOML reconocido por `codex mcp get`; opciones ajenas preservadas | PASS | `preflight.json` |
| Discovery OAuth/OIDC, issuer, resource, scope y JWKS | PASS | `preflight.json` |
| Callback exacto aceptado; llega al formulario de login | PASS, HTTP200 | `preflight.json` |
| Callback distinto rechazado | PASS, HTTP400 | `preflight.json` |
| PKCE ausente o plain rechazado | PASS, HTTP302 con error OAuth `invalid_request` al callback validado | `preflight.json` |
| MCP sin bearer o con bearer inválido rechazado | PASS, HTTP401 con resource metadata | `preflight.json` |
| Token endpoint: código inválido sin client secret | PASS negativo: `invalid_grant`, no éxito de emisión | `preflight.json` |
| Regresión unitaria MCP/OIDC | 10 PASS | `unit_tests.log` |
| Script interactivo: compilación, `--help`, Ruff | PASS estático; no prueba su ejecución OAuth | Comandos ejecutados en esta fase |
| Login y consentimiento humanos con `ti-codex` | **PENDIENTE** | Requiere §4 |
| Emisión, firma, issuer/audience/scope y refresh real | **PENDIENTE** | Requiere §4 |
| initialize, tools/list y seis herramientas con tokens `ti-codex` | **PENDIENTE** | Requiere §4 |
| Herramienta desde Codex App | **PENDIENTE** | Confirmación explícita del dueño |

La primera aserción negativa PKCE esperaba HTTP400. Keycloak devolvía
correctamente un redirect302 con error OAuth al callback permitido; se corrigió
la expectativa del test y se repitió todo el preflight. Se conserva
`preflight_initial_failure.json`. No se cambió la política PKCE para pasar el test.

Las pruebas confidenciales de `ti-chatgpt` anteriores **no sustituyen** las
pruebas pendientes de `ti-codex`. Tampoco un login del script Python equivale
a una conexión E2E de Codex App.

## 4. Intervención necesaria para completar las pruebas técnicas

**El agente se detuvo antes de introducir credenciales.** No hay un flujo
CLI dejado en espera. Para completar emisión/refresh y las seis herramientas:

1. No pulses Autenticarse en App mientras corre este verificador: ambos usan
   el puerto43219. Si quedó abierta una pestaña de los sondeos previos, ciérrala;
   su proceso fue cancelado y no sirve para completar la conexión.
2. En PowerShell, desde `C:\Users\steve\Desktop\Big_Data2`, ejecuta:

   ```powershell
   .\.venv\Scripts\python.exe scripts\verify_codex_oauth_interactive.py --interactive
   ```

3. En el navegador que abra, comprueba el dominio
   `ti-136-114-21-18.sslip.io` y que el cliente es **Codex native MCP / ti-codex**.
   Inicia sesión tú mismo con tu cuenta autorizada y acepta el consentimiento
   `ti:read`. No envíes usuario, contraseña, URL completa ni tokens al agente.
4. Vuelve a la terminal. El script recibe el callback en loopback, comprueba
   state/issuer, canjea el código con S256, valida la firma RS256 y los claims,
   renueva el token y verifica rotación; después ejecuta initialize,
   tools/list y las seis herramientas reales usando el token renovado.
5. El resultado sanitizado será
   `docs/evidence/codex_diagnosis/interactive_validation.json`.
   Dime **«terminó el verificador»** para revisar el resultado y repetir el
   preflight. No declares PASS si aparece FAIL, timeout o alguna prueba pendiente.

El script no lee contraseñas ni almacenes OAuth de Codex, no ejecuta password
grant y no guarda tokens/códigos/verifier. El puerto solo escucha en127.0.0.1;
se cierra al terminar. El login caduca tras5min y puede repetirse. Es un cliente
de prueba compatible con el flujo nativo, **no el cliente Codex App**.

## 5. Pasos exactos en Codex App para conexión E2E

Después de terminar/cerrar el verificador anterior:

1. Abre Codex App en este mismo equipo y host local. Recarga su configuración;
   si conserva la anterior, cierra y vuelve a abrir App.
2. En su configuración de **servidores MCP**, selecciona la entrada existente
   **`big_data_ii_-_threat_intelligence`**. No la vuelvas a registrar con otra URL.
3. Pulsa **«Autenticarse»**. No introduzcas token, client secret ni headers.
4. En Keycloak, inicia sesión personalmente y acepta consentimiento para
   `ti-codex`. Permite el regreso a la dirección local127.0.0.1.
5. Vuelve a App y pide explícitamente:

   ```text
   Usa el MCP big_data_ii_-_threat_intelligence y ejecuta
   get_vulnerability_statistics. Muestra total_cves y as_of.
   ```

6. Confirma que App muestra el servidor autenticado y que hubo una llamada
   real a esa herramienta, no solo una respuesta del modelo. Comunica el
   resultado y un timestamp sin datos de autenticación.

**E2E sigue PENDIENTE hasta esa confirmación.** Un resultado exitoso del
verificador Python no cambia este estado por sí solo.

## 6. Errores y correcciones acotadas

| Error | Acción |
|---|---|
| DCR403 Trusted Hosts | App no está usando el client ID aplicado o usa otro CODEX_HOME/host. Revisar la entrada efectiva; no abrir DCR. |
| `Invalid parameter: redirect_uri` | Comparar localmente host, puerto y path con el callback registrado. No compartir code/state. No añadir `*`; comprobar primero la versión/host de App. |
| Puerto43219 ocupado / callback no carga | Cerrar el otro proceso OAuth propio y repetir Autenticarse. No terminar procesos desconocidos ni abrir puertos cloud. |
| Navegador muestra callback de una prueba anterior | Esa sesión fue cancelada. Iniciar una nueva desde App o desde el verificador. |
| `invalid_grant` tras login | Código expirado, usado o PKCE/session desparejados. Reiniciar el flujo completo, no copiar códigos entre procesos. |
| Token válido pero MCP401/403 | Revisar en memoria issuer, audience exacta y `ti:read`, sin imprimir JWT. Conservar status y etapa; no desactivar verificación. |
| App usa distinto callback | Detenerse y revisar su binario/config efectiva; no afirmar compatibilidad GUI ya probada ni ampliar la allowlist a ciegas. |
| Script no abre navegador | Ejecutarlo en una sesión Windows interactiva con navegador predeterminado. No enviar las credenciales al agente. |
| Launcher npm dice `node: not found` | El binario nativo comprobado funciona; no es un error OAuth del servidor. No se modificó Node/PATH en esta tarea. |

## 7. Rollback sin afectar ChatGPT

1. Cerrar los flujos de login propios de `ti-codex`.
2. En `config.toml`, retirar únicamente los dos ajustes globales agregados,
   `scopes = ["openid", "ti:read"]` de esta entrada y su tabla OAuth con
   `client_id = "ti-codex"`. Conservar `enabled`, URL y toda opción ajena.
3. Comparar con la copia privada indicada en §1. Restaurar el archivo completo
   solo si no hubo cambios posteriores del dueño; no sobrescribir trabajo nuevo.
4. Mediante Admin API privada autenticada, localizar el cliente con GET
   `/auth/admin/realms/ti/clients?clientId=ti-codex` y deshabilitar **solo ese ID**
   con PUT `/auth/admin/realms/ti/clients/{id}`, `enabled=false`, preservando
   sus otros campos. No abrir administración pública ni imprimir credenciales.
5. No borrar/modificar `ti-chatgpt`, scopes compartidos, políticas, volúmenes,
   CVE ni infraestructura. Las pruebas no modificaron DAG ni su scheduling.

Referencia histórica: [diagnóstico y causa raíz](codex_mcp_diagnosis.md).
