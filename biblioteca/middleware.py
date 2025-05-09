import logging
from django.conf import settings
from django.shortcuts import render



logger = logging.getLogger(__name__)

class StrictAPIAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.allowed_origins = set(getattr(settings, 'CORS_ALLOWED_ORIGINS', []))

    def __call__(self, request):
        path = request.path
        rutas_restringidas = ['/api/', '/media/']  # rutas protegidas

        if any(path.startswith(ruta) for ruta in rutas_restringidas):
            origin = request.headers.get('Origin')
            referer = request.headers.get('Referer')

            logger.info(f"Path: {path}, Origin: {origin}, Referer: {referer}")

            # Si no hay Origin ni Referer, se deniega
            if not origin and not referer:
                logger.warning("Denied due to missing Origin and Referer")
                return render(request, '403.html', status=403)

            # Si hay Origin pero no está permitido
            if origin and origin not in self.allowed_origins:
                logger.warning(f"Denied due to disallowed Origin: {origin}")
                return render(request, '403.html', status=403)

            # Si hay Referer pero no empieza por un origen permitido
            if referer:
                referer_ok = any(referer.startswith(allowed) for allowed in self.allowed_origins)
                if not referer_ok:
                    logger.warning(f"Denied due to disallowed Referer: {referer}")
                    return render(request, '403.html', status=403)

        return self.get_response(request)
