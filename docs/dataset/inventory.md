# Inventario inicial NVD

Inspección local: 10 de noviembre de 2026. Archivos JSON completos analizados
con la biblioteca estándar de Python, sin reserialización ni cargas a bases.

| Ruta relativa | Bytes | SHA-256 |
| --- | ---: | --- |
| `data/raw/nvd/2024/nvdcve-2.0-2024.json` | 293745058 | `777bc4d2eea97ef6bbb0a0597b505c10a6c40968388678a7d22b9f45b70a6682` |
| `data/raw/nvd/2025/nvdcve-2.0-2025.json` | 295852585 | `17485621d19368646fd12c7681517e96bd1606f001ffe74b4b0567e3f54ba78d` |
| `data/raw/nvd/2026/nvdcve-2.0-2026.json` | 527484894 | `bbffab4cfabfe5f69adadf5ad056382c89f5953206d57dd504a6ac57d8dba687` |

Los valores anteriores se calcularon antes del traslado y se verifican de nuevo
en destino. Se conservan nombres y bytes originales.

## Formato observado

- Objeto raíz con `resultsPerPage`, `startIndex`, `totalResults`, `format`,
  `version`, `timestamp` y `vulnerabilities`.
- `format = NVD_CVE`, `version = 2.0`, `startIndex = 0` en los tres archivos.
- Tamaño del arreglo `vulnerabilities` igual a `totalResults` y `resultsPerPage`:
  39,369 (2024), 45,482 (2025), 86,940 (2026).
- Marcas temporales declaradas por los feeds: `2026-11-09T03:01:35.3962771`,
  `2026-11-09T03:01:04.0633371` y `2026-11-09T03:00:01.5741499`, respectivamente.

Total: **171,791 entradas**, **1,117,082,537 bytes**. El conteo de entradas no
equivale aún a CVE únicos o registros que superen futuras reglas de calidad.
Falta validar semántica, campos opcionales, duplicados y fechas internas.
