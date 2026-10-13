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
