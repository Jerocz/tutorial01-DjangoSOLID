# Tutorial 01 - Django SOLID

Arquitectura de Software 2026 - EAFIT
Jeronimo Carvajal Zuluaga

Evolucion de la funcionalidad "Compra Rapida" desde una vista desordenada (FBV) hasta una vista que solo delega a la capa de servicio.

## Versiones de la vista

| Version | URL | Donde esta la logica |
|---|---|---|
| FBV spaghetti | `/compra-rapida/fbv/<id>/` | Todo dentro de la funcion |
| CBV | `/compra-rapida/cbv/<id>/` | En el metodo `post` de la clase |
| CBV + Service Layer | `/compra-rapida/<id>/` | En `CompraRapidaService` (services.py) |

La version final usa `BancoNacionalProcesador` (infra/gateways.py), que registra cada pago en `pagos_locales_JERONIMO_CARVAJAL.log`.

## Como correrlo

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Para crear datos de prueba se usa `python manage.py shell`:

```python
from tienda_app.models import Libro, Inventario
l = Libro.objects.create(titulo="Clean Code en Python", precio=150.0)
Inventario.objects.create(libro=l, cantidad=10)
```

Luego entrar a http://127.0.0.1:8000/compra-rapida/1/ y darle "Comprar Ya".
