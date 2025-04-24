
from django.db.models import Q
from django.contrib.auth import authenticate, get_user_model
from django.shortcuts import get_object_or_404
from django.core.files.storage import default_storage
from django.conf import settings
from django.http import JsonResponse
from django.core.exceptions import ValidationError

from ninja import NinjaAPI, Schema, Field, Router
from ninja.security import HttpBasicAuth, HttpBearer
from ninja.files import UploadedFile

import secrets
import hashlib
import csv
import traceback
import os
import re

from typing import List, Optional, Union, Dict

from pydantic import validator

# Importación de modelos (si usas wildcard, de lo contrario importa solo lo que necesites)
from .models import *
from datetime import date

api = NinjaAPI()

router = Router()

User = get_user_model()

# Autenticació bàsica
class BasicAuth(HttpBasicAuth):
    def authenticate(self, request, username, password):
        user = authenticate(username=username, password=password)
        if user:
            # Genera un token simple
            token = secrets.token_hex(16)
            user.auth_token = token
            user.save()
            return token
        return None

# Autenticació per Token Bearer
class AuthBearer(HttpBearer):
    def authenticate(self, request, token):
        try:
            user = User.objects.get(auth_token=token)
            return user
        except User.DoesNotExist:
            return None

# Endpoint per obtenir un token
@api.get("/token", auth=BasicAuth())
@api.get("/token/", auth=BasicAuth())
def obtenir_token(request):
    return {"token": request.auth}

# Esquema de respuesta
class AuthResponse(Schema):
    exists: bool
    grupos: List[str] = []
    token: Optional[str] = None  

# Esquema para recibir las credenciales
class LoginSchema(Schema):
    username: str
    password: str

@api.post("/login", response=AuthResponse)
def login(request, payload: LoginSchema):
    username = payload.username
    password = payload.password
    user = authenticate(username=username, password=password)
    
    if user:
        grupos = [group.name for group in user.groups.all()]
        telefon = getattr(user, "telefon", None)

        if grupos and telefon:
            primer_grupo = grupos[0]
            grupo_encriptado = hashlib.sha256(primer_grupo.encode()).hexdigest()
            telefon_encriptado = hashlib.sha256(telefon.encode()).hexdigest()
            token = f"{grupo_encriptado}_{telefon_encriptado}"
        else:
            token = None

        return {
            "exists": True,
            "grupos": grupos,
            "token": token
        }
    else:
        return {"exists": False, "grupos": [], "token": None}

# Esquema de respuesta para perfil
class UserProfileRequest(Schema):
    username: str

class UserProfileResponse(Schema):
    username: str
    nombre: str
    email: str
    centre: Optional[str] = None
    grup: Optional[str] = None
    imatge: Optional[str] = None
    grupos: list[str]
    telefon: Optional[str] = None

@api.post("/perfil/", response=UserProfileResponse)
def perfil(request, data: UserProfileRequest):
    user = get_object_or_404(User, username=data.username)
    nombre = user.get_full_name() if user.first_name or user.last_name else ""
    centre_name = user.centre.nom if user.centre else None
    grup_name = user.grup.nom if user.grup else None
    try:
        imatge_url = user.imatge.url if user.imatge else None
    except ValueError:
        imatge_url = None
    telefon = user.telefon if user.telefon else None
    grupos = [group.name for group in user.groups.all()]
    return {
        "username": user.username,
        "nombre": nombre,
        "email": user.email,
        "centre": centre_name,
        "grup": grup_name,
        "imatge": imatge_url,
        "grupos": grupos,
        "telefon": telefon,
    }

# Esquema para actualización de los campos editables
class PerfilUpdateSchema(Schema):
    username: str
    imatge: Optional[str] = None
    email: Optional[str] = None
    telefon: Optional[str] = None

# Esquema para la respuesta de la verificación de cambios
class PerfilCheckResponse(Schema):
    modified: bool

@api.post("/verificar-cambios/", response=PerfilCheckResponse)
def verificar_cambios(request, data: PerfilUpdateSchema):
    user = get_object_or_404(User, username=data.username)
    current_imatge = user.imatge.url if user.imatge else None
    modified = (
        (current_imatge != data.imatge) or
        (user.email != data.email) or
        (user.telefon != data.telefon)
    )
    return {"modified": modified}

@api.patch("/perfil/")
def actualizar_perfil(request, data: PerfilUpdateSchema):
    user = get_object_or_404(User, username=data.username)
    
    if data.imatge is not None:
        user.imatge = data.imatge  
    if data.email is not None:
        user.email = data.email
    if data.telefon is not None:
        user.telefon = data.telefon

    user.save()
    return {"success": True}



# catalogo y ejemplares

class CatalegOut(Schema):
    id: int
    titol: str
    autor: Optional[str] = None  # campo para mostrar solo el nombre del autor

    class Config:
        orm_mode = True


    @validator('autor', pre=True)
    def extract_autor(cls, value):
        # Si ya es None, devolvemos None.
        if value is None:
            return None
        # Si value es un objeto con atributo 'nom', lo devolvemos.
        try:
            return value.nom
        except AttributeError:
            return value

        

class LlibreOut(CatalegOut):
    ISBN: Optional[str]
    editorial: Optional[str] = None

    @validator('editorial', pre=True)
    def extract_editorial(cls, value):

        if value is None:
            return None
        try:
            return value.nom
        except AttributeError:
            return value


class ExemplarOut(Schema):
    id: int
    registre: str
    exclos_prestec: bool
    baixa: bool
    cataleg: Union[LlibreOut,CatalegOut]
    tipus: str
    centre: dict

class LlibreIn(Schema):
    titol: str
    editorial: str


@api.get("/llibres", response=List[LlibreOut])
@api.get("/llibres/", response=List[LlibreOut])
#@api.get("/llibres/", response=List[LlibreOut], auth=AuthBearer())
def get_llibres(request, search: str = None):

    # Devuelve todos los llibres. Si se proporciona el parámetro 'search',
    # se filtran los llibres cuyo titol o autor contenga el término de búsqueda.

    if search:
        qs = Llibre.objects.filter(
            Q(titol__icontains=search) | Q(autor__nom__icontains=search)
        ).select_related('autor', 'editorial')
    else:
        qs = Llibre.objects.all().select_related('autor', 'editorial')
    return qs



@api.post("/llibres/")
def post_llibres(request, payload: LlibreIn):
    llibre = Llibre.objects.create(**payload.dict())
    return {
        "id": llibre.id,
        "titol": llibre.titol
    }



@api.get("/llibres/{id}", response=LlibreOut)
def get_llibre_by_id(request, id: int):
    llibre = get_object_or_404(Llibre, id=id)
    return llibre

@api.get("/exemplars", response=List[ExemplarOut])
@api.get("/exemplars/", response=List[ExemplarOut])
def get_exemplars(request):
    # carreguem objectes amb els proxy models relacionats exactes
    exemplars = Exemplar.objects.select_related(
        "cataleg__llibre",
        "cataleg__revista",
        "cataleg__cd",
        "cataleg__dvd",
        "cataleg__br",
        "cataleg__dispositiu",
        "centre",
    ).all()
    result = []

    for exemplar in exemplars:
        cataleg_instance = exemplar.cataleg

        # Determinar el tipus de l'objecte Cataleg
        if hasattr(cataleg_instance, "llibre"):
            cataleg_schema = LlibreOut.from_orm(cataleg_instance.llibre)
            tipus = "llibre"
        #elif hasattr(cataleg_instance, "dispositiu"):
        #    cataleg_schema = LlibreOut.from_orm(cataleg_instance.dispositiu)
        # TODO: afegir altres esquemes
        else:
            cataleg_schema = CatalegOut.from_orm(cataleg_instance)
            tipus = "indefinit"

        # Afegir l'Exemplar amb el Cataleg serialitzat
        result.append(
            ExemplarOut(
                id=exemplar.id,
                registre=exemplar.registre,
                exclos_prestec=exemplar.exclos_prestec,
                baixa=exemplar.baixa,
                cataleg=cataleg_schema,
                tipus=tipus,
                centre={
                    "id": exemplar.centre.id,
                    "nom": exemplar.centre.nom
                },
                
            )
        )

    return result

class UsuariCSV:
    def __init__(self, nom: str, cognom1: str, cognom2: str, email: str, telefon: str, centre: str, grup: str):
        self.nom = nom
        self.cognom1 = cognom1
        self.cognom2 = cognom2
        self.email = email
        self.telefon = telefon
        self.centre = centre
        self.grup = grup

    def to_dict(self):
        return {
            "nom": self.nom,
            "cognom1": self.cognom1,
            "cognom2": self.cognom2,
            "email": self.email,
            "telefon": self.telefon,
            "centre": self.centre,
            "grup": self.grup
        }

class UploadResponse(Schema):
    mensaje: str
    errores: Optional[List[Dict]] = None
    usuarios_creados: Optional[int] = 0

def validar_nombre(nombre):
    # Ejemplo de validación: no vacío y solo letras
    if not nombre:
        raise ValueError("El nombre está vacío.")
    if not nombre.isalpha():
        raise ValueError(f"Nombre inválido: '{nombre}' contiene caracteres no permitidos.")

def validar_telefono(telefono):
    # Validación simple: debe ser numérico y contener al menos 9 dígitos
    if not telefono or not telefono.isdigit() or len(telefono) < 9:
        raise ValueError("Teléfono inválido. Debe contener al menos 9 dígitos numéricos.")

@api.post("/subir-documento/", response={200: UploadResponse, 500: UploadResponse})
def subir_documento(request, archivo: UploadedFile):
    file_path = default_storage.save(f"temp/{archivo.name}", archivo)
    full_path = os.path.join(settings.MEDIA_ROOT, file_path)

    registros: List[UsuariCSV] = []
    errores: List[Dict] = []
    usuarios_creados = 0

    try:
        with open(full_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                cleaned_row = {key.strip(): (value.strip() if value is not None else "") for key, value in row.items()}

                if not any(cleaned_row.values()):
                    continue

                email = (cleaned_row.get("email") or "").strip().replace(' ', '').lower()

                if not email or "@" not in email:
                    errores.append({"fila": cleaned_row, "error": "Email vacío o inválido"})
                    continue

                if Usuari.objects.filter(username=email).exists():
                    errores.append({"fila": cleaned_row, "error": f"El email {email} ya existe."})
                    continue

                nom = (cleaned_row.get("nom") or "").strip()
                cognom1 = (cleaned_row.get("cognom1") or "").strip()
                cognom2 = (cleaned_row.get("cognom2") or "").strip()
                telefon = cleaned_row.get("telefon", "")
                centre_nom = cleaned_row.get("centre", "")
                grup_nom = cleaned_row.get("grup", "")

                if not all([nom, cognom1, cognom2, telefon, centre_nom, grup_nom]):
                    errores.append({"fila": cleaned_row, "error": "Faltan campos obligatorios."})
                    continue

                try:
                    validar_nombre(nom)
                    validar_nombre(cognom1)
                    if cognom2:
                        validar_nombre(cognom2)
                    validar_telefono(telefon)

                    centre, _ = Centre.objects.get_or_create(nom=centre_nom)
                    grup, _ = Grup.objects.get_or_create(nom=grup_nom)

                    Usuari.objects.create_user(
                        username=email,
                        email=email,
                        first_name=nom,
                        last_name=f"{cognom1} {cognom2}",
                        telefon=telefon,
                        centre=centre,
                        grup=grup,
                        password="1234"
                    )
                    usuarios_creados += 1

                    registros.append(UsuariCSV(
                        nom=nom,
                        cognom1=cognom1,
                        cognom2=cognom2,
                        email=email,
                        telefon=telefon,
                        centre=centre_nom,
                        grup=grup_nom
                    ))

                except (ValidationError, ValueError) as e:
                    errores.append({"fila": cleaned_row, "error": str(e)})
                    continue

    except Exception as e:
        print("Error procesando CSV:", e)
        traceback.print_exc()
        return 500, {
            "mensaje": f"Error interno del servidor: {e}",
            "errores": [],
            "usuarios_creados": 0
        }


    finally:
        try:
            os.remove(full_path)
        except:
            pass

    return 200, {
        "mensaje": f"{usuarios_creados} usuario(s) creados correctamente.",
        "usuarios_creados": usuarios_creados,
        "errores": errores
    }






# prestamos

class PrestecOut(Schema):
    id: int
    data_prestec: date
    data_retorn: Optional[date] = None
    anotacions: Optional[str] = None
    exemplar_titol: str

class PrestecsRequest(Schema):
    username: str

@api.post("/prestecs", response=List[PrestecOut])
def get_prestecs(request, payload: PrestecsRequest):
    username = payload.username
    qs = Prestec.objects.filter(usuari__username=username).order_by("-data_prestec")
    
    results = []
    for prestec in qs:
        exemplar_titol = prestec.exemplar.cataleg.titol if prestec.exemplar and prestec.exemplar.cataleg else "N/A"
        results.append({
            "id": prestec.id,
            "data_prestec": prestec.data_prestec,
            "data_retorn": prestec.data_retorn,
            "anotacions": prestec.anotacions,
            "exemplar_titol": exemplar_titol,
        })
    return results


#para prestamo del biblio en detalle libro

# Autenticación basada en el token
class AuthBearer(HttpBearer):
    def authenticate(self, request, token):
        try:
            # Buscar al usuario con el token proporcionado
            user = get_user_model().objects.get(auth_token=token)
            # Aquí puedes añadir la verificación del grupo específico del bibliotecario si lo deseas
            return user
        except get_user_model().DoesNotExist:
            return None

# Esquema de búsqueda de usuarios
class UserSearchSchema(Schema):
    query: str

class UserSearchResponse(Schema):
    id: int
    first_name: str
    last_name: str
    email: str
    telefon: Optional[str]
    centre: Optional[str]

# Endpoint para buscar usuarios, protegido por autenticación con token
@api.post("/buscar_usuarios/", response=List[UserSearchResponse])
def buscar_usuarios(request, data: UserSearchSchema):
    try:
       # user = request.auth
        #if not user:
         #   return {"error": "No se pudo autenticar el usuario."}

        query = data.query.strip()

        if not query:
            return {"error": "El campo de búsqueda no puede estar vacío."}

        # Filtrar usuarios según la búsqueda
        usuari = User.objects.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query) |
            Q(telefon__icontains=query),
            groups__name="usuari"
        ).distinct()

        if not usuari:
            logger = logging.getLogger(__name__)
            logger.debug("No se encontraron usuarios.")
            return {"message": "No se encontraron usuarios."}

        return [
            UserSearchResponse(
                id=u.id,
                first_name=u.first_name,
                last_name=u.last_name,
                email=u.email,
                telefon=u.telefon,
                centre=u.centre.nom if u.centre else None
            )
            for u in usuari
        ]

    except Exception as e:
        # Captura y log de la excepción
        logger = logging.getLogger(__name__)
        logger.error(f"Error al buscar usuarios: {str(e)}")
        return {"error": f"Ha ocurrido un error interno: {str(e)}"}


#crear prestamo biblio
class CrearPrestecRequest(Schema):
    usuari: int
    exemplar: int
    data_prestec: Optional[date] = None
    anotacions: Optional[str] = None

@api.post("/crear_prestec")
def crear_prestec(request, payload: CrearPrestecRequest):
    try:
        usuari = Usuari.objects.get(id=payload.usuari)
        exemplar = Exemplar.objects.get(id=payload.exemplar)

        # Creamos el préstamo
        prestec = Prestec.objects.create(
            usuari=usuari,
            exemplar=exemplar,
            data_prestec=payload.data_prestec or date.today(),
            anotacions=payload.anotacions or ""
        )

        # Marcamos el ejemplar como exclòs del préstec
        exemplar.exclos_prestec = True
        exemplar.save()

        return {
            "message": "Préstamo creado correctamente",
            "id": prestec.id
        }

    except Usuari.DoesNotExist:
        return {"error": "Usuari no trobat"}, 404
    except Exemplar.DoesNotExist:
        return {"error": "Exemplar no trobat"}, 404
    except Exception as e:
        return {"error": str(e)}, 500
