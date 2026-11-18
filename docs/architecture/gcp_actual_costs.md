# Costos GCP — estimación vigente, no factura

> **Referencia histórica anterior a la expansión de Cassandra.** Las cifras, pruebas y comandos son de su corte original, no instrucciones vigentes para GCP. Para la arquitectura y operación actuales, consultar [el cierre distribuido](../audits/distributed_final_closure.md).

Catálogo oficial consultado medianteAPICloudBilling:
`docs/evidence/gcp_official_skus.json`. Regiónus-central1,USD,on-demand.
Estimación aplicada al despliegue real (una VM std4, discos 30+100GiB,
IP reservada, buckets privados, AR, Secret Manager, observabilidad).

| Concepto | Estimado USD/día |
|---|---:|
| e2-standard-4,24h,4vCPU16GiB |3.21655|
|130GiBpd-balanced zonales |0.42740|
|UnaIPv4externa |0.12000|
|GCSraw/processed/backups,reserva |0.05000|
|ArtifactRegistry5GB |0.01644|
|SecretManager,reserva |0.03000|
|Logging/Monitoring,reserva |0.10000|
|EgresoInternet1GB/día,reserva |0.12000|
|**Total** |**4.0804**|
|**Con20%contingencia** |**4.8965**|

Preapplygate:`gcp_preapply_cost_gate.json`. Memoria/CPUconSKUoficiales:
CF4E-A0C7-E3BF(core0.02181159/h),F449-33EC-A5EF(RAM0.00292353/GiBh).
DiscozonalSKU6AE1-525F-8B80(0.10/GiBmes),noSKUregionalreplicado0.20.
Mes730h.Loscostosvariables tienen reservas,suposición deusoacadémicobajo.
SinCloudRun,NAT,balanceadores,VMsadicionales niGPU.

Fuentes complementarias oficiales:
- https://cloud.google.com/vpc/network-pricing
- https://cloud.google.com/storage/pricing
- https://cloud.google.com/artifact-registry/pricing
- https://cloud.google.com/secret-manager/pricing
- https://cloud.google.com/stackdriver/pricing

**Costofacturado real:no consultado/no disponible.** No inventarUSD0como factura.
Créditos:S/1000referenciales,no saldoverificado.S/3.75/USDessupuesto,no cotización.
ApagarVMdetieneCPU/RAM,no discos,GCS,imágenes,secretos oIPestática retenida.
UnIPreservada mantieneOAuth/DNSestable,tiene costo aunconVMdetenida.

## Alertas presupuestarias

LaSAimpersonada no tiene`billing.budgets.create/list`. Elusuariogcloudtampoco
pudo listar presupuestos:bilingaccountPERMISSION_DENIED.
`gcp_budget_permissions.json`,`gcp_budget_creation.json`.
**No se creó presupuesto.** Unadministradordefacturación debe crear alerta
mensualUSD150filtradasolo aesteproyecto,umbrales50/75/90/100%.
No cambiarplanfacturación niasignarpermisosglobales ainstanciaspara resolverlo.
Alertasno bloqueangasto; revisar usodiariamente/egresoyapagar trasexposición.
