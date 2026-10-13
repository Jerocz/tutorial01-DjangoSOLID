# Tutorial 01 - Jeronimo Carvajal Zuluaga

Arquitectura de Software 2026 - EAFIT

La logica de la compra rapida (inventario, calculo del IVA y pago) se movio de la vista a `CompraRapidaService` en services.py. Asi la vista final (`CompraRapidaServiceView`) solo recibe la peticion, llama al servicio y muestra el resultado.

## tienda_app/services.py

```python
from django.shortcuts import get_object_or_404
from .models import Libro, Inventario, Orden
from .domain.logic import CalculadorImpuestos

class CompraService:
    """
    SERVICE LAYER: Orquesta la interacción entre el dominio, 
    la infraestructura y la base de datos.
    """
    def __init__(self, procesador_pago):
        # Inyectamos la dependencia (DIP)
        self.procesador_pago = procesador_pago

    def obtener_detalle_producto(self, libro_id):
        libro = get_object_or_404(Libro, id=libro_id)
        total = CalculadorImpuestos.obtener_total_con_iva(libro.precio)
        return {"libro": libro, "total": total}

    def ejecutar_compra(self, libro_id, cantidad):
        # 1. Obtener datos
        libro = get_object_or_404(Libro, id=libro_id)
        inv = get_object_or_404(Inventario, libro=libro)

        # 2. Validar Reglas de Negocio
        if inv.cantidad < cantidad:
            raise ValueError("No hay suficiente stock para completar la compra.")

        total = CalculadorImpuestos.obtener_total_con_iva(libro.precio)

        # 3. Procesar Infraestructura (Pago)
        pago_exitoso = self.procesador_pago.pagar(total)
        
        if not pago_exitoso:
            raise Exception("La transacción fue rechazada por el banco.")

        # 4. Persistencia de efectos secundarios
        inv.cantidad -= cantidad
        inv.save()
        
        Orden.objects.create(libro=libro, total=total)
        
        return total


class CompraRapidaService:
    """
    Tutorial 01: servicio para la compra rapida.
    Saca de la vista toda la logica (inventario, impuestos y pago).
    """
    def __init__(self, procesador_pago):
        # el procesador se inyecta, el servicio no sabe que banco es (DIP)
        self.procesador_pago = procesador_pago

    def obtener_detalle(self, libro_id):
        libro = get_object_or_404(Libro, id=libro_id)
        total = CalculadorImpuestos.obtener_total_con_iva(libro.precio)
        return {'libro': libro, 'total': total}

    def procesar(self, libro_id):
        libro = get_object_or_404(Libro, id=libro_id)
        inv = get_object_or_404(Inventario, libro=libro)

        if inv.cantidad <= 0:
            raise ValueError("No hay existencias.")

        total = CalculadorImpuestos.obtener_total_con_iva(libro.precio)

        if self.procesador_pago.pagar(total):
            inv.cantidad -= 1
            inv.save()
            Orden.objects.create(libro=libro, total=total)
            return total

        raise ValueError("El pago fue rechazado.")

```

## tienda_app/views.py

```python
import datetime

from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views import View

from .infra.gateways import BancoNacionalProcesador
from .models import Inventario, Libro, Orden
from .services import CompraRapidaService, CompraService


class CompraView(View):
    """
    CBV: Vista Basada en Clases.
    Actúa como un "Portero": recibe la petición y delega al servicio.
    """
    template_name = 'tienda_app/compra.html'

    # Configuramos el servicio con su implementación de infraestructura
    def setup_service(self):
        gateway = BancoNacionalProcesador()
        return CompraService(procesador_pago=gateway)

    def get(self, request, libro_id):
        servicio = self.setup_service()
        contexto = servicio.obtener_detalle_producto(libro_id)
        return render(request, self.template_name, contexto)

    def post(self, request, libro_id):
        servicio = self.setup_service()
        try:
            total = servicio.ejecutar_compra(libro_id, cantidad=1)
            return render(request, self.template_name, {
                'mensaje_exito': f"¡Gracias por su compra! Total: ${total}",
                'total': total
            })
        except (ValueError, Exception) as e:
            # Manejo de errores de negocio transformados a respuesta de usuario
            return render(request, self.template_name, {
                'error': str(e)
            }, status=400)


# ---------------------------------------------------------------
# TUTORIAL 01 - Compra Rapida
# Se dejan las 3 versiones para ver la evolucion del codigo
# ---------------------------------------------------------------

# Paso 1: FBV "spaghetti" (todo mezclado en la vista)
def compra_rapida_fbv(request, libro_id):
    libro = get_object_or_404(Libro, id=libro_id)

    if request.method == 'POST':
        # VIOLACION SRP: Logica de inventario en la vista
        inventario = Inventario.objects.get(libro=libro)
        if inventario.cantidad > 0:
            # VIOLACION OCP: Calculo de negocio hardcoded
            total = float(libro.precio) * 1.19

            # VIOLACION DIP: Proceso de pago acoplado al file system
            with open("pagos_manuales.log", "a") as f:
                f.write(f"[{datetime.datetime.now()}] Pago FBV: ${total}\n")

            inventario.cantidad -= 1
            inventario.save()
            Orden.objects.create(libro=libro, total=total)

            return HttpResponse(f"Compra exitosa: {libro.titulo}")
        else:
            return HttpResponse("Sin stock", status=400)

    total_estimado = float(libro.precio) * 1.19
    return render(request, 'tienda_app/compra_rapida.html', {
        'libro': libro,
        'total': total_estimado
    })


# Paso 2: CBV, ya separa GET y POST pero la logica sigue en la vista
class CompraRapidaView(View):
    template_name = 'tienda_app/compra_rapida.html'

    def get(self, request, libro_id):
        libro = get_object_or_404(Libro, id=libro_id)
        total = float(libro.precio) * 1.19
        return render(request, self.template_name, {
            'libro': libro,
            'total': total
        })

    def post(self, request, libro_id):
        # La logica de negocio aun reside aqui, pero separada del GET
        libro = get_object_or_404(Libro, id=libro_id)
        inv = Inventario.objects.get(libro=libro)
        if inv.cantidad > 0:
            total = float(libro.precio) * 1.19
            inv.cantidad -= 1
            inv.save()
            Orden.objects.create(libro=libro, total=total)
            return HttpResponse("Comprado via CBV")
        return HttpResponse("Error", status=400)


# Paso 3: Vista final, solo es un puente entre la web y el servicio
class CompraRapidaServiceView(View):
    template_name = 'tienda_app/compra_rapida.html'

    def get(self, request, libro_id):
        servicio = CompraRapidaService(BancoNacionalProcesador())
        return render(request, self.template_name, servicio.obtener_detalle(libro_id))

    def post(self, request, libro_id):
        try:
            total = CompraRapidaService(BancoNacionalProcesador()).procesar(libro_id)
            return render(request, self.template_name, {'mensaje_exito': f"Compra exitosa. Total: ${total}"})
        except ValueError as e:
            return render(request, self.template_name, {'error': str(e)}, status=400)

```
