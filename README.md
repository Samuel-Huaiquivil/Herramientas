# Control de Herramientas (Django + DRF + PostgreSQL)

Sistema para controlar el alquiler de herramientas y maquinaria ligera a subcontratistas.

- **Activos** con estado trazable: Disponible, En uso, Mantenimiento, Dado de baja (cada cambio queda en el historial).
- **Entrega y devolución** con firma digital simulada (canvas) del responsable de obra y cobro calculado por días iniciados.
- **Mantenimiento preventivo** por fecha límite y/o horas de uso; un activo con mantenimiento vencido no se puede entregar.
- Sesiones + permisos por grupo (Administrador, Bodega, Consulta). API REST en `/api/` (activos, prestamos, planes).

