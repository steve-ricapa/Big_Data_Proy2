# Estimación de costos GCP

**Estimación de planificación, no cotización**, 10/11/2026. Región us-central1,
Linux on-demand, sin Spot, CUD, free tier ni impuestos. Tipo de cambio supuesto
**S/3.75 por USD** (no cotización financiera): S/1,000 ≈ **USD 266.67**.
Mes de cálculo de uso: 720 horas; precios unitarios redondeados. La factura
puede usar otros prorrateos. Revisar calculadora y SKUs antes de aprobar.

## Fuentes y supuestos

Consulta oficial realizada: precios Compute y VPC. El listado Compute actual
redirige a tablas dinámicas; no se obtuvo una cotización regional exportada.
Referencia oficial aproximada de e2-standard-4: USD 0.134/h en el artículo
[Google Cloud AutoML](https://cloud.google.com/blog/topics/developers-practitioners/building-scalable-mlops-system-vertex-ai-automl-and-pipeline/).
Se usa **0.134/h** (4/16 GiB) y **0.067/h** (2/8 GiB, supuesto proporcional).
Son referencias redondeadas, **no precios exactos confirmados para noviembre**.

En [VPC pricing](https://cloud.google.com/vpc/network-pricing) sí se comprobó:
IPv4 externa de VM normal en uso USD **0.005/h**, efímera se libera al apagar;
salida Premium a Sudamérica **0.19/GiB**, interzona **0.01/GiB**, entrada gratis.

Otros valores utilizados como hipótesis que deben reconfirmarse por SKU:

| Recurso | Hipótesis unitaria | Fuente oficial para confirmar |
| --- | --- | --- |
| pd-balanced | 0.10 USD/GiB-mes aprovisionado | https://cloud.google.com/compute/disks-image-pricing |
| GCS Standard regional | 0.020 USD/GiB-mes | https://cloud.google.com/storage/pricing |
| Artifact Registry | 0.10 USD/GB-mes | https://cloud.google.com/artifact-registry/pricing |
| Secret Manager | 0.06 USD/versión activa-mes + operaciones | https://cloud.google.com/secret-manager/pricing |
| Logs | 0.50 USD/GiB ingerido, sin descontar franquicia | https://cloud.google.com/stackdriver/pricing |
| Cloud Run | Reserva de uso, no tarifa plana | https://cloud.google.com/run/pricing |
| VM | Validar región/series/imagen antes del plan | https://cloud.google.com/compute/all-pricing |
| Calculadora | Exportar estimación con fecha antes de aplicar | https://cloud.google.com/products/calculator |

Reserva compartida A/B **USD 12/mes**: GCS 4 GiB = 0.08; imágenes 3 GB = 0.30;
9 versiones activas de secretos = 0.54; operaciones GCS/secretos = 0.50;
5 GiB logs = 2.50; 5 GiB egress a Perú = 0.95; Cloud Run = 5.00;
métricas y margen menor = 2.13. Son límites de estimación, no límites técnicos.
Run supone uso intermitente: 3 servicios × ~10 h activas/mes, 1 CPU/512 MiB,
concurrencia baja; validar precio por solicitud, RAM, WebSockets y arranques.
USD 5 **no alcanza para 3 servicios activos 24/7**.

C usa reserva compartida de **USD 30/mes**: incluye lo anterior, mayor uso Run,
logs y margen para unos 100 GiB interzona (USD 1). No contempla backup completo
periódico, snapshots retenidos, restauraciones, soporte ni licencias Enterprise.
Estos se presupuestarán por separado; no afirmar que costo de backups es cero.

## Comparación (todo encendido 24/7)

| Concepto | A económico | B equilibrado | C distribuido de referencia |
| --- | ---: | ---: | ---: |
| VMs | 1 × std4 | 2 × std4 + 1 × std2 | 7 × std4 + 1 × std2 |
| vCPU / RAM total | 4 / 16 GiB | 10 / 40 GiB | 30 / 120 GiB |
| Compute USD/h | 0.134 | 0.335 | 1.005 |
| Discos totales (boot + datos) | 130 GiB | 390 GiB | 1040 GiB |
| Discos USD/mes | 13.00 | 39.00 | 104.00 |
| IPv4 efímeras USD/h | 0.005 | 0.015 | 0.040 |
| Reserva compartida USD/mes | 12.00 | 12.00 | 30.00 |
| **Total USD/h amortizado** | **0.174** | **0.421** | **1.231** |
| **USD/día** | **4.17** | **10.10** | **29.55** |
| **USD/7 días** | **29.19** | **70.70** | **206.83** |
| **USD/30 días** | **125.08** | **303.00** | **886.40** |
| **Días con USD 266.67** | **64.0** | **26.4** | **9.0** |

Fórmula: hora = compute + IP + (discos + reserva compartida)/720;
día = hora×24; presupuesto/día = autonomía. Redondear solo al mostrar.
Discos B: cada VM 30+100; C: cada VM 30+100. No incluyen HA de Neo4j.
Una ampliación de disco no es fácilmente reversible sin migrar datos.

Recomendación: A durante los seis días restantes ≈ **USD 25.02 / S/93.83**
con este modelo; guardar **30% del presupuesto** como contingencia. A 30 días
≈ S/469.05; B y C exceden S/1,000 en un mes. C puede consumir ~78% en una semana.

## Riesgos y apagado

- VMs apagadas dejan de cobrar CPU/RAM, pero **discos siguen cobrando**: A
  USD 13/mes sin compute. Persisten además GCS, secretos, imágenes y retenciones.
- IP efímera se libera al apagar; estática retenida puede seguir facturando,
  incluso USD 0.01/h si queda sin asignar. No se reserva estática en este código.
- No cuotas de gasto duras: `max_instance_count=1` no limita todas las partidas
  y pueden coexistir revisiones. WebSockets/streaming mantienen sesiones activas.
- Soft delete GCS 7 días puede seguir generando almacenamiento tras borrar.
- Consultas sin paginación, compaction, reintentos, logs verbosos o escaneos
  desde dashboard incrementan CPU, disco y red. No registrar documentos/secretos.
- Configurar alertas de presupuesto 50/75/90/100% en Billing manualmente;
  alertas **no detienen consumo**. Revisar facturación diaria y fecha de créditos.
- Apagar al terminar cada sesión y retirar recursos tras evidencia final.
