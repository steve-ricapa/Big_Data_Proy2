# Estimación GCP — 10 noviembre 2026

> **Referencia histórica anterior a la expansión de Cassandra.** Las cifras, pruebas y comandos son de su corte original, no instrucciones vigentes para GCP. Para la arquitectura y operación actuales, consultar [el cierre distribuido](../audits/distributed_final_closure.md).

**Estimación, no factura ni aprobación para desplegar.** us-central1, Linux, on-demand, sin CUD/Spot, impuestos ni descuentos. Mes 730 h. Conversión ilustrativa S/3.75/USD, no tipo de cambio bancario: S/1000 ≈ USD266.67.

Se obtuvo HTML oficial de [General purpose VM pricing](https://cloud.google.com/products/compute/pricing/general-purpose), fila `e2-standard-4`: **USD0.13402284/h** (4vCPU,16GiB). Los encabezados regionales son dinámicos: reconfirmar SKU/región con calculadora antes de autorizar; no tratar extracción de fila como cotización contractual. e2-standard-8 se estima al doble USD0.26804568/h; escenario extendido dos std4 al doble también.

Discos pd-balanced: supuesto USD0.10/GiB-mes. [Fuente](https://cloud.google.com/compute/disks-image-pricing). Guardar 30GiB boot +100GiB datos = USD13/mes. GCS Standard regional, supuesto USD0.020/GiB-mes: 2GiB ≈USD0.04/mes, más operaciones. [Fuente](https://cloud.google.com/storage/pricing). Imágenes 3GB, supuesto USD0.10/GB-mes = USD0.30, [Artifact Registry](https://cloud.google.com/artifact-registry/pricing). Secretos 9 versiones, supuesto USD0.06/versión-mes =USD0.54 + accesos, [Secret Manager](https://cloud.google.com/secret-manager/pricing). Estas tarifas auxiliares son hipótesis que deben reconfirmarse, no SKU exportados en esta ejecución.

| Escenario | VM USD/h | Disco USD/mes | Reserva auxiliar USD/mes | Total USD/h amortizado | USD/día | USD/mes |
|---|---:|---:|---:|---:|---:|---:|
| Mínimo / recomendado académico: 1 std4, todos los contenedores | .134023 | 13 | 12 | .168269 | 4.04 | 122.84 |
| Más margen RAM: 1 std8, sin HA | .268046 | 13 | 12 | .302292 | 7.26 | 220.67 |
| Extendido: 2 std4, separación parcial | .268046 | 26 | 25 | .337909 | 8.11 | 246.67 |

Fórmula: `(VM_h ×730 + discos + reserva)/730`. Mínimo seis días ≈USD24.23 =S/90.86 amortizado; con discos retenidos un mes y solo 48h de VM, ~USD6.43 compute +USD13 disco + auxiliares según uso. No facturación real observada. 1 std4 es recomendado por costo y validación local con límites; std8 solo si medición de memoria lo exige.

Reserva auxiliar es margen, no tarifa: GCS, registry, secretos, logs, salida y una posible IPv4 temporal. IP externa/egress **no aprobados** por defecto Terraform. [VPC pricing](https://cloud.google.com/vpc/network-pricing): considerar IP aprox USD0.005/h y transferencia a Internet según destino (hipótesis conservadora USD0.19/GiB a Sudamérica). Ejemplo 5GiB=USD0.95; entrada usualmente gratis. Sin habilitar APIs ni generar tráfico cloud. Cloud Run opcional queda vacío y no es necesario para demo local; no suponer Streamlit WebSockets 24/7 gratis. [Cloud Run pricing](https://cloud.google.com/run/pricing).

## Riesgos presupuestarios
Discos/snapshots/buckets/versiones siguen costando con VM apagada; reservas y secretos no desaparecen al detener contenedores. No comprometer contratos anuales ni usar HA para esta entrega. Logs sin rotación, soft delete, salida interzona y sesiones web permanentes suman cargos. Presupuesto no limita automáticamente gasto; alertas requieren aprobación explícita para crearlas. Reservar 30% contingencia y revisar Billing diariamente si se autoriza despliegue.

El plan real en `docs/evidence/terraform_plan.txt` propone **37 altas, 0 cambios, 0 bajas**; no se aplicó. No hay recursos de este plan ejecutados ni evidencia cloud de la aplicación. Filas oficiales de ambas VM extraídas en `docs/evidence/gcp_price_reference.json`;el selector regional requiere reconfirmación. Ver plan previo `gcp-deployment-plan.md`, operación `gcp-operations.md` y limitaciones de bootstrap antes de cualquier despliegue.
