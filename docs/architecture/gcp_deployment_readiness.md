# Plan vigente de despliegue GCP

Revisión: 10/11/2026. Proyecto `proyectobigdata2-514216`.
**Preparación y consultas de solo lectura; despliegue NO autorizado ni ejecutado.**

## 1. Conexión comprobada ahora

| Prueba real | Resultado |
|---|---|
| Proyecto configurado en gcloud | `proyectobigdata2-514216` |
| Consulta del proyecto con usuario gcloud | PASS, ProyectoBigData2, ACTIVE |
| Estado de facturación del proyecto | `billingEnabled=true`; no se consultó saldo ni se modificó facturación |
| Renovación de credenciales ADC | PASS, sin imprimir tokens ni abrir archivos de credenciales directamente |
| Consulta Service Usage con ADC | HTTP200, listado completo de23 APIs habilitadas |
| Consulta Resource Manager con ADC/cuenta impersonada | HTTP403, `SERVICE_DISABLED` |
| Terraform validate | PASS |
| Terraform plan actual | **37altas,0cambios,0bajas** |

La autenticación funciona. El403 observado no demuestra credenciales inválidas:
la respuesta identifica Cloud Resource Manager deshabilitada. Tampoco demuestra
que todos los permisos necesarios para crear recursos estén comprobados.
Un plan sin recursos existentes/datasources puede aprobar sin ejercer llamadas
de creación; no sustituye preflight de APIs, IAM, cuotas y disponibilidad.

Evidencias: `docs/evidence/gcp_connection_check.json` y
`docs/evidence/gcp_deployment_plan_latest.txt`. El plan textual no es un plan
binario aprobado para aplicar. No se modificaron ADC ni configuración gcloud.

Repetir prueba ADC sin instalar dependencias en el proyecto:

```powershell
uv run --no-project --python 3.11 --with google-auth --with requests python scripts/verify_gcp_connection.py
gcloud projects describe proyectobigdata2-514216
gcloud billing projects describe proyectobigdata2-514216 --format="json(projectId,billingEnabled)"
```

## 2. Arquitectura recomendada para esta entrega

- Una VM `e2-standard-4`,4vCPU/16GiB,`us-central1-a`,Debian12.
- Arranque30GiB y datos100GiB `pd-balanced`, volumen de datos persistente.
- MongoDB,Cassandra,Neo4j,PostgreSQL,Airflow **3.4.0**,API y dashboard en Docker.
- Acceso académico **por túneles SSH sobre IAP**, no web pública ni puertos
  públicos de bases. Mantener API/dashboard/Airflow en loopback y motores en
  red interna Docker; no publicar27017/9042/7687.
- Sin Cloud Run inicial (`web_services={}`),GKE,Composer,Cloud NAT ni balanceador.
- GCS,Artifact Registry,Secret Manager ytelemetría según módulos existentes.
  Secret Manager Terraform crea contenedores de secretos, no valores en state.
- MCP stdio opcional para un operador de confianza; no conector ChatGPT remoto.

Los motores y flujo ya funcionan localmente:42tests yreplay Airflow de171791
CVE. No reconstruirlos ni volver a Airflow2.11. Los37recursos incluyen cuentas
web reservadas por el módulo IAM, aunque no se crean servicios Cloud Run.

## 3. Bloqueos y decisiones antes del apply

### APIs (habilitación requiere autorización)

No aparecen habilitadas en el inventario actual:

- `compute.googleapis.com`: VM,discos,VPC/firewall.
- `iam.googleapis.com`: cuentas de servicio.
- `cloudresourcemanager.googleapis.com`: IAM de proyecto yconsultas del proyecto.
- `artifactregistry.googleapis.com`: repositorio de imágenes.
- `secretmanager.googleapis.com`: recursos de secretos.
- `iap.googleapis.com` y `oslogin.googleapis.com`: acceso operativo seguro propuesto.
- `iamcredentials.googleapis.com`: revisar explícitamente antes de nuevas
  operaciones de impersonación; ADC refresh sí funcionó en esta prueba, aunque
  no figura habilitada en el proyecto listado. No inferir su estado en otros
  proyectos de cuota/consumo ni reconfigurar ADC para resolverlo a ciegas.

Service Usage,Storage,Logging yMonitoring sí figuran habilitadas.
Cloud Run API solo si se aprueba una fase posterior con Cloud Run.
No se habilitó ninguna API durante esta revisión.

### Salida a Internet

El default `allow_external_egress_ip=false` no permite apt/Docker Hub/NVD.
Opción mínima propuesta: aprobar IP externa **efímera** para salida, firewall
sin ingresos públicos, SSH exclusivamente IAP. No IP estática ni NAT.
El siguiente plan deberá llevar `allow_external_egress_ip=true` si se elige
esa opción y volver a revisar costo/exposición. Alternativa: imagen yartefactos
preconstruidos accesibles por Private Google Access, aún por preparar.

### Bootstrap, seguridad y operación

- Confirmar imagen Debian fijada: el plan usa
  `projects/debian-cloud/global/images/debian-12-bookworm-v20261109`;
  verificar existencia/estado mediante Compute API cuando esté habilitada.
- Consultar cuotas CPU/disco/IP ydisponibilidad zonal; plan no reserva capacidad.
- Confirmar permisos del operador IAP/OS Login yuso de la identidad de VM.
  No crear claves JSON ni conceder Owner a identidades runtime.
- Revisar overlay para VM,permisos de filesystem,secretos privados yrotación.
  No subir el directorio local `secrets/`, ADC ostate Terraform en el paquete.
- El bootstrap actual **se detiene si el disco está vacío**. Inicializar
  explícitamente solo el disco nuevo aprobado, confirmar montaje en `/srv/ti-data`
  yreiniciar bootstrap. No automatizar formateo a ciegas ni usar disco de sistema.
- Adaptar volúmenes Compose al disco persistente; verificar respaldos/restore.
- Cassandra auth/RBAC yTLS siguen pendientes antes de habilitar acceso de
  clientes a motores. El piloto cerrado por IAP no es aprobación productiva:
  revisar el riesgo incluso con motores aislados en una sola VM.
- DAG inicialmente pausado. Nunca ejecutar Airflow yCLI/CRUD simultáneamente.

## 4. Secuencia de despliegue propuesta

1. **Aprobar alcance/costo:** una VM/discos,APIs,IPefímera de salida ytransferencia
   del código/dataset. Sin aprobación, detenerse antes de mutaciones cloud.
2. Habilitar únicamente APIs aprobadas yrepetir verificación ADC/API; consultar
   cuotas,imagen,IAM yrecursos existentes para evitar colisiones.
3. Preparar configuración VM/IAP,volúmenes,bootstrap ysecretos. Generar nuevo
   plan con las decisiones aprobadas; revisar recursos ysalida a Internet.
4. Aplicar **solo el plan revisado**; registrar nombres,fecha ycostos estimados.
   `apply` no se ejecutó yno forma parte de esta solicitud de preparación.
5. Conectar por IAP,inicializar únicamente disco nuevo,montar e instalar Docker.
6. Transferir código/artefactos aprobados ylos tres JSON (~1.12GB); validar SHA256.
   Crear secretos de entorno por un canal privado,sin logs ni claves permanentes.
7. Construir/obtener imágenes,arrancar motores,bootstrap usuarios Mongo yAirflow3.
   Primera carga cloud desde JSON; no asumir que volúmenes locales existen allí.
8. Ejecutar CRUD,incrementalidad,KPI,42tests,API yreplay completo Airflow;
   confirmar171791 CVE por motor yparidad ID/hash,capturar evidencias cloud reales.
9. Abrir dashboard/API/Airflow con túneles IAP privados,demostrar,pausar DAG.
10. Apagar VM tras demo yrevisar retención/backups. Discos/buckets/repositorios
    retenidos siguen costando. Borrado requiere autorización separada; el disco
    tiene `prevent_destroy` yla VM protección de borrado.

## 5. Presupuesto y límites

Estimación vigente previa: **USD4.04/día oUSD122.84/mes**,730horas/mes,
S/3.75 por USD como supuesto: ~S/15.15/día,~S/460.65/mes.
Seis días continuos: ~USD24.24/~S/90.90 antes de contingencia.
Reservar30% para variación,imágenes,operaciones,discos ytransferencias.
No se verificó saldo de créditos; facturación habilitada no garantiza S/1000
disponibles. Confirmar precios/región yfacturación antes de autorizar gasto.
Ver `gcp_cost_estimate.md`; no es cotización ni costo real facturado.

**Conclusión:** conexión autenticada confirmada; plan Terraform generado.
Despliegue bloqueado por APIs ydecisiones de aprovisionamiento/seguridad,
no por necesidad de volver a iniciar sesión. No se crearon recursos.
