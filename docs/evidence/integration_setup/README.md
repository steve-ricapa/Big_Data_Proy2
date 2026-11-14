# Evidencia de documentación E2E y conexión ChatGPT — 11/11/2026

Estas pruebas nuevas no sustituyen ni recalifican los artefactos de aceptación v2.
No se modificó OAuth, IAM, infraestructura o datos CVE para escribir los documentos.

| Archivo | Contenido seguro |
|---|---|
| keycloak_runtime.json | Allowlist de configuración del cliente/realm, scopes, mappers y versiones; sin client secret |
| secret_reference.json | Recurso/key de Secret Manager y booleanos de coincidencia con runtime; nunca valores |
| mcp_live.json | Discovery, challenge401, initialize, schemas, claims públicos seleccionados y estado de refresh |
| tools_execution.json | Argumentos y respuestas públicas NVD de las seis herramientas |
| http.json | Comprobaciones HTTPS/API nuevas y total del snapshot |
| gcp_inventory.json | Inventario nuevo GCS/registro/secretos-metadata/alertas; Billing403 |
| local_tests.log | Nueva regresión Windows47 PASS/8 SKIP; no prueba cloud |
| validation.json | Validación documental, huellas y comprobación de ausencia de los valores privados usados por los verificadores |

El primer ensayo de refresh fue posterior a un code replay negativo y falló;
se conserva `mcp_live.log`. El ensayo final separó la concesión normal de esa
prueba negativa, renovó con post/basic y ejecutó las seis herramientas.
`mcp_live_final.log` y los JSON finales son la referencia de esta fase.

Ninguna prueba se ejecutó desde una cuenta ChatGPT. El campo
`chatgpt_account_connected=false` se mantiene explícito.
