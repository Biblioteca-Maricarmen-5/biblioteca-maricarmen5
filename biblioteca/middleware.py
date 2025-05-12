import logging
import re
from django.conf import settings
from django.shortcuts import render
from django.http import JsonResponse

logger = logging.getLogger(__name__)

class StrictAPIAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.allowed_origins = set(getattr(settings, 'CORS_ALLOWED_ORIGINS', []))
        
        # Rutas restringidas (requieren validación de origen)
        self.restricted_paths = [
            re.compile(r'^/api/'),                          # Todas las rutas API
            re.compile(r'^/media/?$'),                     # Ruta media
            re.compile(r'^/media/temp(/|$)'),              # Media temp
            re.compile(r'^/media/usuaris(/|$)'),           # Media usuarios
        ]
        
        # Rutas excepcionales (no requieren validación)
        self.whitelisted_paths = [
            re.compile(r'^/api/auth/google/?$'),           # Autenticación Google
            re.compile(r'^/api/auth/google/callback/?$'),  # Callback Google (si lo usas)
        ]

    def __call__(self, request):
        path = request.path
        method = request.method
        
        # 1. Permitir peticiones OPTIONS (CORS preflight)
        if method == 'OPTIONS':
            return self.get_response(request)
        
        # 2. Verificar si la ruta está en la lista blanca
        if any(p.match(path) for p in self.whitelisted_paths):
            logger.debug(f"Whitelisted path accessed: {path}")
            return self.get_response(request)
        
        # 3. Verificar si la ruta está restringida
        if any(p.match(path) for p in self.restricted_paths):
            origin = request.headers.get('Origin')
            referer = request.headers.get('Referer')
            
            logger.info(f"Restricted path access attempt - Path: {path}, Method: {method}, Origin: {origin}, Referer: {referer}")
            
            # Validación de origen
            if not self._is_origin_allowed(origin, referer):
                logger.warning(f"Access denied to {path} - Origin: {origin}, Referer: {referer}")
                return self._deny_access(request)
        
        return self.get_response(request)
    
    def _is_origin_allowed(self, origin, referer):
        """Verifica si el origen o referer están permitidos"""
        # Permitir sin origen/referer en desarrollo
        if settings.DEBUG and (not origin and not referer):
            return True
            
        # Validar origen
        if origin and origin in self.allowed_origins:
            return True
            
        # Validar referer
        if referer:
            return any(
                referer.startswith(allowed) or 
                referer.startswith(allowed.replace('https://', 'http://'))
                for allowed in self.allowed_origins
            )
        
        return False
    
    def _deny_access(self, request):
        """Respuesta para acceso denegado"""
        if request.headers.get('Accept') == 'application/json':
            return JsonResponse(
                {'error': 'Acceso no autorizado'}, 
                status=403
            )
        return render(request, '403.html', status=403)