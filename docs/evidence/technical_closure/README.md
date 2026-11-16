# Evidencias del cierre técnico — 16/11/2026

No sumar suites repetidas ni convertir SKIP o confirmaciones manuales en tests
automatizados. Datos y fechas son del corte de cada artefacto, no constantes.

| Artefacto | Qué acredita |
|---|---|
| `terraform.json` | fmt/init/validate reales en export limpio del índice Git; backend desactivado, lockfile readonly y sin apply. |
| `runtime.json` | Escaneo completo de ID/hash en tres motores, esquemas/índices reales, 14 contrastes de KPI/consistencia, historial Airflow y lecturas HTTP. No llama herramientas MCP ni modifica esquemas. |
| `dashboard_canary.json` | 15 comprobaciones AppTest sobre el código candidato contra API/bases reales, antes de activar. |
| `dashboard_deployed.json` | Mismas comprobaciones sobre el archivo instalado después de activar. No contar como 30 tests diferentes. |
| `dashboard_activation.json` | Solo dashboard recreado; otros12 IDs idénticos, hashes de fuentes, imagen previa para rollback. |
| `dashboard_browser.json` | agent-browser/Chrome por HTTPS con Basic Auth existente; cinco vistas, filtros, SVG y página3 del grafo. |
| `screenshots/*.png` | Capturas reales de esas cinco vistas; no diseños ni imágenes históricas. |
| `mcp_manual_confirmation.json` | Confirmación del dueño de uso exitoso desde Codex App. No suite automatizada nueva. |
| `validation.json` | Resultados consolidados locales, documentación, seguridad del índice y configuración. |
| `browser_initial_failure.json` | Error del primer probe: esperaba canvas, pero Vega-Lite usa SVG. Conservado y corregido sin alterar la aplicación para ocultarlo. |

Los logs de pytest/Ruff/Terraform se conservan localmente (`*.log` excluido de
Git); los resultados consolidados versionables están en los JSON y auditoría.
Una prueba nueva de política Git falló inicialmente por CRLF del stdin Windows;
se corrigió usando protocolo NUL, no cambiando la política para aceptar secretos.
Los intentos iniciales de transporte con el Python bundled de gcloud fallaron
antes de ejecutar la activación; se usó Python3.11 existente sin cambiar gcloud.

## Repetición segura

Desde la raíz del proyecto, tras instalar las dependencias dev/MCP bloqueadas:

```powershell
uv run --extra dev --extra mcp pytest -q -p no:cacheprovider
uv run --extra dev --extra mcp ruff check src services tests airflow/dags scripts
terraform fmt -check -recursive infrastructure/terraform
terraform -chdir=infrastructure/terraform/environments/dev init -backend=false -lockfile=readonly -input=false
terraform -chdir=infrastructure/terraform/environments/dev validate
```

La integración de dashboard requiere `API_URL` accesible, Python con Streamlit
y la aplicación instalada; lee solamente:

```powershell
$env:API_URL = 'http://127.0.0.1:18000'
.\.venv\Scripts\python.exe scripts/verify_dashboard_readonly.py
```

Las integraciones de pytest con `TI_INTEGRATION=1` incluyen CRUD y pruebas de
permisos que intentan escribir. **No habilitarlas sobre producción para repetir
este cierre.** La integración de lectura tiene su script separado.

No se incluyen valores de Basic Auth, contraseñas, tokens, state ni tfvars.
La autenticación web del navegador usó únicamente el secreto web existente,
transferido en memoria por IAP y por stdin al proceso de browser automation;
sin modificarlo ni leer credenciales OAuth/Keycloak. No publicar HAR/auth state.
