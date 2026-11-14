# Guion de defensa — 24 minutos

Antes: Docker saludable, carga terminada, sin pipeline activo paralelo, dashboard
`http://127.0.0.1:18501`, OpenAPI `http://127.0.0.1:18000/docs`, Airflow 3
`http://127.0.0.1:18081`. Iniciar con `scripts/start-local.ps1 -WithAirflow`.
No mostrar secretos ni otras aplicaciones. Evidencia principal vigente:
`docs/evidence/acceptance_v2/` y `final_acceptance_v2.md`.
`revalidation_*` y `airflow34_*` son cortes históricos. Docker local puede
estar detenido: no presentar sus pruebas como cloud. Comandos desde raíz.

| Tiempo | Mostrar y explicar | Comando / evidencia | Resultado esperado |
|---|---|---|---|
| 0–2 min | Problema, objetivos; CVE no es ataque | README + informe §1–4 | Aclarar alcance académico y 3 modelos |
| 2–4 min | Dataset original, volumen y hashes | `Get-Content docs/evidence/inventory.json` | 3 feeds /171791 entradas; no confundir con únicos cargados |
| 4–6 min | Arquitectura y particiones | Mermaid system.md y modelos | Mongo raw, Cassandra por consulta, Neo4j relaciones |
| 6–9 min | DAG y ejecución | Airflow Graph/Grid + `airflow_dag_test.log` | Siete tareas reales exitosas; explicar retries y paths XCom |
| 9–11 min | Integridad entre motores | Abrir `acceptance_v2/final_state.json`; contraste con `acceptance/vm_probe.json` histórico | Mismo total y huella en tres motores; identificar fecha exacta |
| 11–14 min | CRUD cloud de los tres motores | Abrir `acceptance_v2/crud.log` y `cloud_tests.log` | 12 PASS, ID temporal y cleanup_verified; 55 tests cloud PASS |
| 14–16 min | Incrementalidad | `docker compose run --rm --no-deps runner selftest --output docs/evidence/incremental_demo.json` | Nuevo/inválido/replay/modificado/obsoleto; mostrar partición antigua eliminada |
| 16–20 min | Dashboard cinco vistas | Overview, Explorer, Analytics, Graph, Pipeline | Total, severidad, media por versión, productos únicos, detalle y relaciones reales |
| 20–22 min | Pruebas y evidencia | Logs/XML `acceptance_v2`; capturas nuevas y restauraciones scratch | 47 PASS/8 SKIP Windows; 55 PASS cloud, sin sumar suites; distinguir restore ejecutado de respaldo subido |
| 22–24 min | Costos, Terraform, límites y cierre | `acceptance_v2/terraform_plan.log`, `rebuild.json` y cierre v2 | GCP aplicado y plan sin deriva; reconstrucción de VM NO ensayada; costo estimado, no factura |

No ejecutar carga total durante exposición: mostrar su evidencia y usar muestras para latencia predecible. Si se solicita demostración del DAG en vivo, con motores saludables y sin otra carga:

```powershell
docker compose -f docker-compose.yml -f docker-compose.airflow3.yml exec -T airflow3-scheduler python /opt/project/scripts/verify_scheduler3.py
```

Esto usa scheduler real con 10000 entradas y fallo/retry deliberado. Puede
tomar 3–5 minutos; mostrar evidencia previa en la exposición de 24 minutos y
reservar ejecución local en vivo para preguntas. No ejecutar este script
en cloud durante la defensa: pausa el DAG al terminar. Cloud debe quedar
ACTIVO para el schedule diario; limit=0 significa completo, no cero entradas.

Extra opcional, no desplazar requisitos obligatorios:
`uv run --extra mcp python scripts/verify_mcp.py` demuestra protocolo MCP real
sin exponer un servicio público. No afirmar conexión remota con ChatGPT.

Consulta Cassandra breve:
```powershell
docker compose exec cassandra cqlsh -e "SELECT cve_id,severity,score FROM threat_intelligence.cves_by_severity WHERE bucket='CRITICAL' AND month='2024-01' LIMIT 5;"
```

Consulta API:
```powershell
Invoke-RestMethod http://127.0.0.1:18000/api/v1/kpis | ConvertTo-Json -Depth 6
Invoke-RestMethod 'http://127.0.0.1:18000/api/v1/vulnerabilities?severity=CRITICAL&page_size=5'
```

Preguntas previsibles: ¿por qué tres bases? modelos complementarios; ¿promedios? separados por versión; ¿producto? identidad parte/vendor/product; ¿fallo intermedio? checkpoint por sink; ¿cloud? desplegado con autorización, una VM y USD4.08/día estimados; ¿Big Data? escala académica, streaming y variedad, no escala industrial.

Contingencia: si una base no responde, mostrar error real y logs, no cifras simuladas. Usar evidencia previa claramente fechada, explicar que no sustituye ejecución actual. Apagado local al finalizar: `powershell -File scripts/stop-local.ps1`, sin borrar volúmenes.

## Sección cloud (desplegado y verificado)

Alternativa o continuación de la demo: plataforma completa en GCP. URLs reales:

- Dashboard/API: `https://ti-136-114-21-18.sslip.io` (Basic Auth `ti-demo`;
  contraseña cloud en Secret Manager/archivo privado de la VM, no usar el
  secreto local ni mostrarla). Cinco vistas con
   **174734 CVE** al cierre v2, tras la sincronización automática11/11 03:00 UTC.
- MCP: `https://ti-136-114-21-18.sslip.io/mcp` (OIDC Keycloak realm `ti`).
- Airflow UI: no pública; túnel IAP:
  `gcloud compute ssh ti-dev-data --tunnel-through-iap --ssh-flag="-L 18081:localhost:18081"`
  y abrir `http://localhost:18081` (login admin, contraseña SimpleAuthManager
  del archivo privado `secrets/airflow3-passwords` de la VM, no la local).

Demostración cloud en 3–4 minutos:

1. Overview del dashboard en HTTPS con autenticación: total174734 y fecha
   de corte KPI; explicar Basic Auth + TLS 1.3 (capturas
   `docs/evidence/screenshots/gcp_dashboard_*.png`).
2. Grid de Airflow por túnel: corridas `scheduled__03:00`, `full34_*` y
   `sync34_*` en SUCCESS; Neo4j try 2 corresponde a los replays full, no a sync34. Explicar watermark tras paridad
   (`gcp_airflow_execution.md`).
3. Sincronización NVD real: última programada11/11 03:00 UTC —2335 registros,
   127 nuevos/802 modificados/1406 unchanged por solape, paridad de huella.
   Restauración GCS de los tres motores:174607 CVE del respaldo02:00,
   anterior al sync03:00; no confundir ese corte con producción174734.
4. Costos y operación: USD 4.08/día estimado con SKU oficiales; respaldo
   02:00 UTC → sync 03:00 UTC; `ti-stack.service` en arranque.

No afirmar conexión ChatGPT sin login real del dueño (pasos en
`gcp_mcp_validation.md`). No mostrar secretos ni consola con datos de otros
proyectos. Evidencia completa: `docs/report/final_acceptance_v2.md`.
