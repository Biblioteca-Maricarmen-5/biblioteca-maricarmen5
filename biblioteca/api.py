from django.contrib.auth import authenticate, get_user_model
from ninja import NinjaAPI, Schema, Field
from ninja.security import HttpBasicAuth, HttpBearer
from .models import *
from django.shortcuts import get_object_or_404
from typing import List, Optional, Union
import secrets
import hashlib

api = NinjaAPI()

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
    cicle: Optional[str] = None
    imatge: Optional[str] = None
    grupos: list[str]
    telefon: Optional[str] = None

@api.post("/perfil/", response=UserProfileResponse)
def perfil(request, data: UserProfileRequest):
    user = get_object_or_404(User, username=data.username)
    nombre = user.get_full_name() if user.first_name or user.last_name else ""
    centre_name = user.centre.nom if user.centre else None
    cicle_name = user.cicle.nom if user.cicle else None
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
        "cicle": cicle_name,
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


class CatalegOut(Schema):
    id: int
    titol: str
    autor: Optional[str]

class LlibreOut(CatalegOut):
    editorial: Optional[str]
    ISBN: Optional[str]

class ExemplarOut(Schema):
    id: int
    registre: str
    exclos_prestec: bool
    baixa: bool
    cataleg: Union[LlibreOut,CatalegOut]
    tipus: str

class LlibreIn(Schema):
    titol: str
    editorial: str


@api.get("/llibres", response=List[LlibreOut])
@api.get("/llibres/", response=List[LlibreOut])
#@api.get("/llibres/", response=List[LlibreOut], auth=AuthBearer())
def get_llibres(request):
    qs = Llibre.objects.all()
    return qs

@api.post("/llibres/")
def post_llibres(request, payload: LlibreIn):
    llibre = Llibre.objects.create(**payload.dict())
    return {
        "id": llibre.id,
        "titol": llibre.titol
    }

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
            )
        )

    return result