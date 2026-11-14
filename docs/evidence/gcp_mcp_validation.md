# Validación MCP remoto en GCP (URL pública)

> Guía de conexión vigente, verificada nuevamente el11/11/2026:
> [`chatgpt_mcp_setup.md`](../integrations/chatgpt_mcp_setup.md).
> Incluye versión de protocolo, refresh y las referencias privadas correctas.

## Resultado final
Servidor MCP `https://ti-136-114-21-18.sslip.io/mcp`, transporte
streamable-http stateless con protección DNS-rebinding. Emisor OIDC real
Keycloak 26.8.2 realm `ti` (`/auth/realms/ti`), cliente confidencial
`ti-chatgpt` PKCE S256 y consentimiento explícito. Verificación completa en
`gcp_mcp_protocol_validation.json` (todas PASS):

- `oauth_authorization_code_pkce_s256` con login+consentimiento del dueño real
- `authorization_code_replay_rejected` (el código no se puede reutilizar)
- Seis herramientas de solo lectura: `search_vulnerabilities`,
  `get_cve_details`, `get_top_cwes`, `get_vulnerability_statistics`,
  `get_affected_products`, `explore_cve_relationships`
- `invalid_identifier_rejected`
- Descubrimiento 200: `/.well-known/oauth-protected-resource/mcp` y OIDC
  issuer config vía RFC8414 (`gcp_https_validation.json`)

JWT verificado en el servidor vía JWKS: firma, emisor, audiencia `/mcp`,
caducidad y scope `ti:read` (pruebas unitarias
`tests/test_remote_mcp.py` y `tests/test_sync.py` — 12 PASS combinados en la
ejecución previa, incluidas firma inválida y
expiración ausente). Rutas de administración Keycloak/master: 404 público.

## Conexión de la cuenta ChatGPT — paso manual del dueño (PENDIENTE)
El servidor está preparado y probado con flujo OAuth completo; conectar la
cuenta ChatGPT exige iniciar sesión interactiva como dueño en el conector de
OpenAI, que un agente no puede ni debe suplantar. Pasos:

1. ChatGPT → Configuración → Conectores / Apps (modo desarrollador).
2. Registrar conector MCP remoto con URL `https://ti-136-114-21-18.sslip.io/mcp`.
3. OAuth del conector: client_id `ti-chatgpt`; el secreto de cliente está en
   Secret Manager: recurso `ti-dev-runtime-bootstrap`, clave JSON
   `mcp-oauth-client-secret`, versión vigente, sin exponerlo.
4. Redirect URIs permitidos ya registrados en el realm:
   `https://chatgpt.com/connector_platform_oauth_redirect`,
   `https://chatgpt.com/connector/oauth/*`, `https://localhost/callback`.
5. Scope solicitado: `ti:read`. Iniciar sesión con el usuario del dueño
   `ti-owner` (contraseña en `ti-dev-runtime-bootstrap`, clave JSON
   `keycloak-user-password`) y
   aceptar el consentimiento.
6. Probar una herramienta de solo lectura (p. ej. `get_vulnerability_statistics`).

`chatgpt_account_connected: false` — no se afirma conexión no verificada desde
ChatGPT. Tras el paso manual, la validación queda cubierta por los checks
anteriores más el uso real del conector.
