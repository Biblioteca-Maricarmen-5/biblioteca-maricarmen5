from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import escape, mark_safe


from .models import *

class CategoriaAdmin(admin.ModelAdmin):
	list_display = ('nom','parent')
	ordering = ('parent','nom')


class UsuariAdmin(UserAdmin):
    # Añadir 'telefon' al formulario de edición y creación
    fieldsets = UserAdmin.fieldsets + (
        ("Dades acadèmiques", {
            'fields': ('centre', 'cicle', 'imatge', 'telefon'),  # Añadimos el campo 'telefon'
        }),
    )
    
    # Añadimos 'telefon' en el formulario de creación
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {
            'fields': ('telefon',),  # Añadimos el campo 'telefon' en el formulario de creación
        }),
    )
    
    # Mostramos el campo 'telefon' en la lista de usuarios
    list_display = UserAdmin.list_display + ('telefon',)

class ExemplarsInline(admin.TabularInline):
	model = Exemplar
	extra = 1
	readonly_fields = ('pk',)
	fields = ('pk','registre','exclos_prestec','baixa')

class LlibreAdmin(admin.ModelAdmin):
	filter_horizontal = ('tags',)
	inlines = [ExemplarsInline,]
	search_fields = ('titol','autor','CDU','signatura','ISBN','editorial','colleccio')
	list_display = ('titol','autor','editorial','num_exemplars')
	readonly_fields = ('thumb',)
	def num_exemplars(self,obj):
		return obj.exemplar_set.count()
	def thumb(self,obj):
		return mark_safe("<img src='{}' />".format(escape(obj.thumbnail_url)))
	thumb.allow_tags = True

admin.site.register(Usuari,UsuariAdmin)
admin.site.register(Categoria,CategoriaAdmin)
admin.site.register(Pais)
admin.site.register(Llengua)
admin.site.register(Llibre,LlibreAdmin)
admin.site.register(Revista)
admin.site.register(Dispositiu)
admin.site.register(Imatge)

class PrestecAdmin(admin.ModelAdmin):
    readonly_fields = ('data_prestec',)
    fields = ('exemplar','usuari','data_prestec','data_retorn','anotacions')
    list_display = ('exemplar','usuari','data_prestec','data_retorn')

class ReservaAdmin(admin.ModelAdmin):
    readonly_fields = ('data',)
    fields = ('exemplar', 'usuari', 'data')
    list_display = ('exemplar', 'usuari', 'data')

admin.site.register(Centre)
admin.site.register(Cicle)
admin.site.register(Reserva, ReservaAdmin)
admin.site.register(Prestec,PrestecAdmin)
admin.site.register(Peticio)


