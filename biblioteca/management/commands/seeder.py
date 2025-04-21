import os
import random
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils.timezone import make_aware
from django.contrib.auth.hashers import make_password
from faker import Faker
from faker.providers import lorem, person, address, company, date_time, misc

# Configurar Faker para que use español de España
fake = Faker('es_ES')
fake.add_provider(lorem)
fake.add_provider(person)
fake.add_provider(address)
fake.add_provider(company)
fake.add_provider(date_time)
fake.add_provider(misc)

from biblioteca.models import (
    Categoria, Pais, Llengua, Llibre, Exemplar, Usuari, Prestec, Reserva,
    Centre, Grup, Revista, CD, DVD, BR, Dispositiu, Imatge, Autor, Editorial
)

def limpiar_db():
    """Opcional: Limpiar la base de datos existente (solo para desarrollo)"""
    print("Limpiando base de datos...")
    from django.db import connection
    cursor = connection.cursor()
    try:
        cursor.execute('SET CONSTRAINTS ALL IMMEDIATE;')
        cursor.execute('SET CONSTRAINTS ALL DEFERRED;')
    except Exception as e:
        print("No se pudo ajustar las constraints:", e)
    
    modelos = [Categoria, Pais, Llengua, Llibre, Exemplar, Usuari, Prestec, Reserva, Centre, Grup, Revista, CD, DVD, BR, Dispositiu]
    for modelo in modelos:
        modelo.objects.all().delete()
    print("Base de datos limpiada")

def crear_categorias():
    print("Creando categorías...")
    categorias_principales = [
        "Literatura", "Ciencia", "Historia", "Arte", "Tecnología",
        "Filosofía", "Economía", "Salud", "Deportes", "Infantil"
    ]
    
    for cat in categorias_principales:
        categoria = Categoria.objects.create(nom=cat)
        # Creación de subcategorías de nivel 1
        for _ in range(random.randint(2, 5)):
            subcat = Categoria.objects.create(
                nom=f"{cat} - {fake.word().capitalize()}",
                parent=categoria
            )
            # Con 30% de probabilidad, se crean subcategorías de nivel 2
            if random.random() < 0.3:
                for __ in range(random.randint(1, 3)):
                    Categoria.objects.create(
                        nom=f"{subcat.nom} - {fake.word().capitalize()}",
                        parent=subcat
                    )

def crear_paises_y_lenguas():
    print("Creando países y lenguas...")
    paises_comunes = [
        "España", "Francia", "Italia", "Reino Unido", "Alemania",
        "Estados Unidos", "México", "Argentina", "China", "Japón"
    ]
    for pais in paises_comunes:
        Pais.objects.create(nom=pais)
    
    lenguas_comunes = [
        "Catalán", "Español", "Inglés", "Francés", "Alemán",
        "Italiano", "Portugués", "Chino", "Japonés", "Ruso", "Árabe"
    ]
    for lengua in lenguas_comunes:
        Llengua.objects.create(nom=lengua)

def crear_autores_y_libros():
    print("Creando autores y libros...")
    # Asegurarse de tener un centro para asignar a los ejemplares
    default_centre = Centre.objects.first()
    if not default_centre:
        default_centre = Centre.objects.create(nom="Esteve Terradas i Illa")

    # Crear instancias de Autor y Editorial
    autors = [Autor.objects.create(nom=fake.name()) for _ in range(100)]
    editorials = [Editorial.objects.create(nom=fake.company()) for _ in range(20)]
    
    paises = list(Pais.objects.all())
    lenguas = list(Llengua.objects.all())
    categorias = list(Categoria.objects.all())
    libros_creados = 0
    ejemplares_creados = 0
    ejemplares_objetivo = 5000
    used_isbns = set()

    #def get_unique_isbn():
     #   while True:
      #      isbn = fake.isbn13()
       #     if isbn not in used_isbns:
        #        used_isbns.add(isbn)
         #       return isbn
    def get_unique_isbn():
        while True:
            try:
                isbn = fake.isbn13().replace('-', '')  # Elimina guiones si los tiene
                if len(isbn) > 13:
                    isbn = isbn[:13]  # Limita a 13 caracteres
                if isbn not in used_isbns:
                    used_isbns.add(isbn)
                    return isbn
            except Exception as e:
                print(f"Error generando ISBN: {e}")
                continue



    # Se crean libros para cada autor creado
    for autor in autors:
        num_libros = random.randint(1, 10)
        for _ in range(num_libros):
            if libros_creados >= 1000:
                break
            titulo = fake.sentence(nb_words=3).replace('.', '').title()
            libro = Llibre.objects.create(
                titol=titulo,
                titol_original=titulo if random.random() < 0.3 else fake.sentence(nb_words=3).replace('.', '').title(),
                autor=autor,
                CDU=fake.numerify("###.##"),
                signatura=f"LB-{fake.bothify('??###')}",
                data_edicio=fake.date_between(start_date='-50y', end_date='today'),
                resum=fake.paragraph(nb_sentences=5),
                anotacions=fake.paragraph(nb_sentences=2) if random.random() < 0.7 else None,
                mides=f"{random.randint(15, 30)}x{random.randint(20, 40)} cm",
                ISBN=get_unique_isbn(),
                editorial=random.choice(editorials),  # Se asigna un objeto Editorial
                colleccio=fake.word().title() if random.random() < 0.5 else None,
                lloc=fake.city(),
                pais=random.choice(paises),
                llengua=random.choice(lenguas),
                numero=random.randint(1, 10) if random.random() < 0.3 else None,
                volums=random.randint(1, 5) if random.random() < 0.2 else None,
                pagines=random.randint(50, 800) if random.random() < 0.9 else None,
                info_url=fake.url() if random.random() < 0.5 else None,
                preview_url=fake.url() if random.random() < 0.3 else None,
                thumbnail_url=fake.image_url(width=200, height=300) if random.random() < 0.4 else None
            )
            libro.tags.set(random.sample(categorias, random.randint(1, 4)))
            libros_creados += 1

            # Cada libro tendrá 5 ejemplares (se ajusta para no superar el objetivo)
            ejemplares_por_libro = 5
            if ejemplares_creados + ejemplares_por_libro > ejemplares_objetivo:
                ejemplares_por_libro = ejemplares_objetivo - ejemplares_creados
            for _ in range(ejemplares_por_libro):
                Exemplar.objects.create(
                    cataleg=libro,
                    registre=f"REG-{fake.bothify('####-####')}",
                    exclos_prestec=random.random() < 0.1,
                    baixa=random.random() < 0.05,
                    centre=default_centre
                )
                ejemplares_creados += 1
                if ejemplares_creados >= ejemplares_objetivo:
                    break
            if libros_creados % 100 == 0:
                print(f"Creados {libros_creados} libros y {ejemplares_creados} ejemplares...")
            if ejemplares_creados >= ejemplares_objetivo:
                break
        if libros_creados >= 1000 or ejemplares_creados >= ejemplares_objetivo:
            break

    # Si aún no se han creado 1000 libros, se crean libros adicionales
    while libros_creados < 1000:
        autor = random.choice(autors)
        titulo = fake.sentence(nb_words=3).replace('.', '').title()
        libro = Llibre.objects.create(
            titol=titulo,
            titol_original=titulo if random.random() < 0.3 else fake.sentence(nb_words=3).replace('.', '').title(),
            autor=autor,
            CDU=fake.numerify("###.##"),
            signatura=f"LB-{fake.bothify('??###')}",
            data_edicio=fake.date_between(start_date='-50y', end_date='today'),
            resum=fake.paragraph(nb_sentences=5),
            anotacions=fake.paragraph(nb_sentences=2) if random.random() < 0.7 else None,
            mides=f"{random.randint(15, 30)}x{random.randint(20, 40)} cm",
            ISBN=get_unique_isbn(),
            editorial=random.choice(editorials),
            colleccio=fake.word().title() if random.random() < 0.5 else None,
            lloc=fake.city(),
            pais=random.choice(paises),
            llengua=random.choice(lenguas),
            numero=random.randint(1, 10) if random.random() < 0.3 else None,
            volums=random.randint(1, 5) if random.random() < 0.2 else None,
            pagines=random.randint(50, 800) if random.random() < 0.9 else None,
            info_url=fake.url() if random.random() < 0.5 else None,
            preview_url=fake.url() if random.random() < 0.3 else None,
            thumbnail_url=fake.image_url(width=200, height=300) if random.random() < 0.4 else None
        )
        libro.tags.set(random.sample(categorias, random.randint(1, 4)))
        libros_creados += 1
    
    # Crear ejemplares adicionales en caso de que aún no se alcance el objetivo
    if ejemplares_creados < ejemplares_objetivo:
        libros = list(Llibre.objects.all())
        while ejemplares_creados < ejemplares_objetivo:
            libro = random.choice(libros)
            Exemplar.objects.create(
                cataleg=libro,
                registre=f"REG-{fake.bothify('####-####')}",
                exclos_prestec=random.random() < 0.1,
                baixa=random.random() < 0.05,
                centre=default_centre
            )
            ejemplares_creados += 1
            if ejemplares_creados % 100 == 0:
                print(f"Creados {ejemplares_creados} ejemplares...")
    
    print(f"Final: {libros_creados} libros y {ejemplares_creados} ejemplares")

def crear_otros_materiales():
    print("Creando otros materiales...")
    categorias = list(Categoria.objects.all())
    paises = list(Pais.objects.all())
    lenguas = list(Llengua.objects.all())
    
    # Aseguramos un centro por defecto
    default_centre = Centre.objects.first()
    if not default_centre:
        default_centre = Centre.objects.create(nom="Esteve Terradas i Illa")
    
    # Revistas (50 unidades)
    for i in range(50):
        revista = Revista.objects.create(
            titol=f"Revista {fake.word().capitalize()} {fake.word().capitalize()}",
            data_edicio=fake.date_between(start_date='-20y', end_date='today'),
            resum=fake.paragraph(nb_sentences=3),
            ISSN=fake.bothify("####-####"),
            editorial=fake.company(),  # Campo CharField, se asigna un string
            lloc=fake.city(),
            pais=random.choice(paises),
            llengua=random.choice(lenguas),
            numero=random.randint(1, 100),
            pagines=random.randint(20, 200)
        )
        revista.tags.set(random.sample(categorias, random.randint(1, 3)))
        for _ in range(random.randint(1, 3)):
            Exemplar.objects.create(
                cataleg=revista,
                registre=f"REV-{fake.bothify('####-####')}",
                exclos_prestec=True,
                baixa=random.random() < 0.05,
                centre=default_centre
            )
    
    # CDs (30 unidades) – en este caso, el campo "discografica" es un CharField
    for i in range(30):
        cd = CD.objects.create(
            titol=f"{fake.word().capitalize()} {fake.word().capitalize()}",
            autor=fake.name(),
            data_edicio=fake.date_between(start_date='-30y', end_date='today'),
            discografica=fake.company(),
            estil=random.choice(["Pop", "Rock", "Clásica", "Jazz", "Electrónica", "Hip-Hop", "Flamenco", "Salsa"]),
            duracio=make_aware(datetime.now() + timedelta(minutes=random.randint(30, 120)))
        )
        cd.tags.set(random.sample(categorias, random.randint(1, 2)))
        for _ in range(random.randint(1, 3)):
            Exemplar.objects.create(
                cataleg=cd,
                registre=f"CD-{fake.bothify('####-####')}",
                exclos_prestec=random.random() < 0.2,
                baixa=random.random() < 0.05,
                centre=default_centre
            )

def crear_centros_y_ciclos():
    print("Creando centros y ciclos formativos...")
    centros = []
    for i in range(5):
        centro = Centre.objects.create(
            nom=f"Instituto {fake.word().capitalize()}"
        )
        centros.append(centro)
    
    ciclos = []
    areas = ["Informática", "Administración", "Comercio", "Sanidad", "Diseño"]
    for area in areas:
        for nivel in ["GS", "GM"]:
            grup = Grup.objects.create(
                nom=f"{nivel} en {area} {fake.word().capitalize()}"
            )
            ciclos.append(grup)
    
    return centros, ciclos

def crear_usuarios_y_prestamos():
    print("Creando usuarios y préstamos...")
    centros, ciclos = crear_centros_y_ciclos()
    usuarios = []
    for i in range(50):
        username = fake.user_name()
        usuario = Usuari.objects.create_user(
            username=username,
            email=fake.email(),
            password=make_password(username),
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            centre=random.choice(centros),
            grup=random.choice(ciclos),
            auth_token=fake.md5()
        )
        usuarios.append(usuario)
    
    ejemplares = list(Exemplar.objects.filter(baixa=False, exclos_prestec=False))
    current_date = datetime.now().date()
    
    for i in range(500):
        ejemplar = random.choice(ejemplares)
        usuario = random.choice(usuarios)
        max_days_ago = min(365, (current_date - datetime(2023, 1, 1).date()).days)
        days_ago = random.randint(7, max_days_ago)
        fecha_prestamo = current_date - timedelta(days=days_ago)
        min_return_date = fecha_prestamo + timedelta(days=1)
        days_range = (current_date - min_return_date).days
        if days_range > 0:
            days_after = random.randint(0, days_range)
            fecha_devolucion = min_return_date + timedelta(days=days_after)
        else:
            fecha_devolucion = min_return_date
        assert fecha_devolucion > fecha_prestamo, f"Error: fecha_devolucion ({fecha_devolucion}) <= fecha_prestamo ({fecha_prestamo})"
        Prestec.objects.create(
            usuari=usuario,
            exemplar=ejemplar,
            data_prestec=fecha_prestamo,
            data_retorn=fecha_devolucion,
            anotacions=fake.sentence() if random.random() < 0.3 else None
        )
        if i % 50 == 0:
            print(f"Creados {i} préstamos...")
    
    for i in range(100):
        Reserva.objects.create(
            usuari=random.choice(usuarios),
            exemplar=random.choice(ejemplares),
            data=fake.date_between(start_date='-6m', end_date='today')
        )

class Command(BaseCommand):
    help = 'Genera datos de prueba en la base de datos'

    def handle(self, *args, **kwargs):
        self.stdout.write("=== INICIANDO GENERACIÓN DE DATOS DE PRUEBA ===")
        self.stdout.write("Este proceso puede tardar varios minutos...")
        
        # Si deseas limpiar la base de datos, descomenta la siguiente línea:
        # limpiar_db()
        
        crear_categorias()
        crear_paises_y_lenguas()
        crear_autores_y_libros()
        # crear_otros_materiales()  # Descomenta si deseas crear otros materiales
        crear_usuarios_y_prestamos()
        
        self.stdout.write("=== GENERACIÓN DE DATOS COMPLETADA ===")
        self.stdout.write(f"Total libros creados: {Llibre.objects.count()}")
        self.stdout.write(f"Total ejemplares creados: {Exemplar.objects.count()}")
        self.stdout.write(f"Total usuarios creados: {Usuari.objects.count()}")
        self.stdout.write(f"Total préstamos creados: {Prestec.objects.count()}")
