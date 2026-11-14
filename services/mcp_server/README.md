# MCP de Threat Intelligence (solo lectura)

Seis herramientas implementadas con el SDK oficial Python, FastMCP: búsqueda,
detalle, CWE, estadísticas, productos y relaciones. Reutiliza la API y sus
consultas; no recibe credenciales de bases, SQL/CQL/Cypher ni URLs arbitrarias.
Los argumentos se validan con el esquema de herramientas y los errores no
revelan configuración. Texto NVD y referencias son datos no confiables, no
instrucciones para el agente. No se abren URLs contenidas en CVE.

## Operación local

```powershell
Set-Location C:\Users\steve\Desktop\Big_Data2
uv sync --locked --extra dev --extra mcp --python 3.11
docker compose build mcp
# API y motores deben estar activos:
docker compose --profile web up -d api dashboard
uv run --extra mcp python scripts/verify_mcp.py
```

Para un cliente MCP con stdio, configurar el proceso:

```json
{
  "mcpServers": {
    "threat-intelligence": {
      "command": "docker",
      "args": ["compose", "--project-directory", "C:\\Users\\steve\\Desktop\\Big_Data2", "run", "--rm", "-T", "--no-deps", "mcp"]
    }
  }
}
```

El cliente debe heredar el entorno normal de Docker Desktop (incluidas las
variables Windows de localización de plugins), no solamente PATH. El servidor
es stdio: mensajes MCP por stdout, logs por stderr. El proceso termina al cerrar
el cliente; no hay puerto público ni credenciales en este archivo de ejemplo.
Autorización local por acceso al proceso/socket Docker: solo usuarios confiables.

Prueba real cliente/servidor: `docs/evidence/mcp_validation.json`, handshake,
lista de seis herramientas, seis consultas y rechazo de identificador inválido.
No confundir tests unitarios de helpers con esta prueba de protocolo.

**ChatGPT remoto no conectado**: el stdio no es un conector HTTP de ChatGPT.
Requerirá transporte Streamable HTTP, HTTPS, autenticación OAuth compatible,
autorización y aprobación de despliegue/costos. No abrir un túnel público sin
esos controles. MCP stdio local está implementado; esa integración remota sigue
pendiente y no bloquea la entrega académica.
