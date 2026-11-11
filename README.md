# Control de Herramientas (Django + DRF + PostgreSQL)

Sistema para controlar el alquiler de herramientas y maquinaria ligera a subcontratistas.

- **Activos** con estado trazable: Disponible, En uso, Mantenimiento, Dado de baja (cada cambio queda en el historial).
- **Entrega y devolución** con firma digital simulada (canvas) del responsable de obra y cobro calculado por días iniciados.
- **Mantenimiento preventivo** por fecha límite y/o horas de uso; un activo con mantenimiento vencido no se puede entregar.
- Sesiones + permisos por grupo (Administrador, Bodega, Consulta). API REST en `/api/` (activos, prestamos, planes).

## Local (Windows, PowerShell)
```powershell
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env        # edita DB_PASSWORD (y crea la base "herramientas" en tu PostgreSQL)
python manage.py makemigrations inventario
python manage.py migrate
python manage.py crear_demo   # grupos, usuarios admin/bodega/consulta (clave cambiar123) y datos de ejemplo
python manage.py runserver
python manage.py test inventario
```
Subcontratistas y obras se administran desde `/admin/`.

## Despliegue
Ver `deploy/DESPLIEGUE_EC2.md`.
