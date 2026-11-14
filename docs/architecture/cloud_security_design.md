# Decisiones de publicación cloud

Despliegue autorizado: una VM16GiB,objetivo USD5/día; bases en red Docker
interna sin publicación de puertos. Caddy terminará TLS; SSH yAirflow solo IAP.
Cloud Run se omite para evitar costos de sesiones Streamlit/conectividad.

MCP remoto usará Streamable HTTP del SDK oficial con servidor OAuth/OIDC
**Keycloak**, no un OAuth artesanal. JWT verificado por firma,JWKS,issuer,
audience,expiración yscope; OAuth Authorization Code con PKCE S256 yconsentimiento.
Cliente ChatGPT estático (ID/secreto configurables en ChatGPT); no se presume
registro dinámico sin probarlo. El propietario deberá completar conexión/login.
No se afirmará compatibilidad final hasta probar MCP autenticado ydocumentar
las capacidades actuales del cliente ChatGPT.

Keycloak,PostgreSQL yCaddy comparten la única VM,limitados en memoria. No se
añaden servicios de identidad facturables externos. Credenciales/realm/db
persistentes yprivados; /admin no público. Dashboard/API mediante Basic Auth
solo sobre HTTPS; endpoints administrativos de Airflow no publicados.

Dominio técnico gratuito dependiente de DNS yACME: verificar dominio/certificado
reales después de asignar IP; no inventar URLs ni dar por garantizada su emisión.
