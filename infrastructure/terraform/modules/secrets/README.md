# Contenedores de secretos (código, no credenciales)

Este módulo declara diez recursos Secret Manager y acceso acotado de la identidad
de VM a nueve de ellos. No crea versiones ni contiene `secret_data`, contraseñas,
tokens o archivos de credenciales. El material runtime se aprovisiona por un
procedimiento privado separado, nunca mediante valores guardados en el state.

`main.tf` debe viajar con el repositorio: `environments/dev/main.tf` lo referencia
con `../../modules/secrets`. La excepción de `.gitignore` solo permite código
`.tf` y este README aquí; los directorios de secretos runtime siguen excluidos.

Validación sin despliegue desde la raíz:

```powershell
terraform -chdir=infrastructure/terraform/environments/dev init -backend=false -lockfile=readonly -input=false
terraform -chdir=infrastructure/terraform/environments/dev validate
```

La validación de sintaxis/esquema no sustituye permisos, inputs aprobados,
filesystem preparado, configuración privada ni restauración de datos. No ejecutar
`apply` para comprobar este módulo ni importar estados ajenos.
