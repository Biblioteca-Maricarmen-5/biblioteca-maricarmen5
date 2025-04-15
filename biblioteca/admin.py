from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import escape, mark_safe
from django.forms.models import BaseInlineFormSet
from django.core.exceptions import ObjectDoesNotExist

from .models import *

# ==== ADMIN PARA CATEGORIA ====
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nom', 'parent')
    ordering = ('parent', 'nom')


# ==== ADMIN PARA USUARI ====
class UsuariAdmin(UserAdmin):
    # Añadir 'telefon' al formulario de edición y creación
    fieldsets = UserAdmin.fieldsets + (
        ("Dades acadèmiques", {
            'fields': ('centre', 'grup', 'imatge', 'telefon'),
        }),
    )
    # Añadimos 'telefon' en el formulario de creación
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {
            'fields': ('telefon',),
        }),
    )
    # Mostramos el campo 'telefon' en la lista de usuarios
    list_display = UserAdmin.list_display + ('telefon',)


# ==== INLINE PARA EXEMPLARS (EJEMPLARES) ====

class ExemplarInlineFormSet(BaseInlineFormSet):
    def save_new(self, form, commit=True):
        instance = super().save_new(form, commit=False)
        # Si no hi ha centre assignat, s'assigna el centre de l'usuari (si existeix)
        if not instance.centre and hasattr(self, 'request') and self.request.user.centre:
            instance.centre = self.request.user.centre
        if commit:
            instance.save()
        return instance

    def save_existing(self, form, instance, commit=True):
        # Si s'està salvant un exemplar existent i no té centre, s'assigna el centre
        if not instance.centre and hasattr(self, 'request') and self.request.user.centre:
            instance.centre = self.request.user.centre
        return super().save_existing(form, instance, commit=commit)


class ExemplarsInline(admin.TabularInline):
    model = Exemplar
    extra = 1
    readonly_fields = ('pk',)
    fields = ('pk', 'registre', 'exclos_prestec', 'baixa', 'centre')
    formset = ExemplarInlineFormSet

    def get_formset(self, request, obj=None, **kwargs):
        FormSet = super().get_formset(request, obj, **kwargs)
        # Definim un formset que rep el request i assigna el centre per a cada formulari,
        # només si l'usuari no és superusuari i té un centre assignat
        class RequestFormSet(FormSet):
            def __init__(self, *args, **kwargs):
                self.request = request
                super().__init__(*args, **kwargs)
                if not request.user.is_superuser and request.user.centre:
                    for form in self.forms:
                        try:
                            _ = form.instance.centre
                        except ObjectDoesNotExist:
                            form.instance.centre = request.user.centre
                            form.initial['centre'] = request.user.centre.pk
        return RequestFormSet

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Si l'usuari no és superusuari, només es mostren els exemplars del seu centre
        if not request.user.is_superuser:
            if request.user.centre:
                return qs.filter(centre=request.user.centre)
            else:
                return qs.none()
        return qs

    def get_readonly_fields(self, request, obj=None):
        # Si l'usuari no és superusuari, el camp 'centre' es fa de només lectura
        if not request.user.is_superuser:
            return self.readonly_fields + ('centre',)
        return self.readonly_fields


# ==== ADMIN PERSONALIZADO PARA LLIBRE ====
class LlibreAdmin(admin.ModelAdmin):
    change_form_template = 'admin/change_form.html'
    filter_horizontal = ('tags',)
    inlines = [ExemplarsInline,]  # Incloem l'inline personalitzat
    search_fields = ('titol', 'autor', 'CDU', 'signatura', 'ISBN', 'editorial', 'colleccio')
    list_display = ('titol', 'autor', 'editorial', 'num_exemplars')
    readonly_fields = ('thumb',)

    def num_exemplars(self, obj):
        return obj.exemplar_set.count()

    def thumb(self, obj):
        return mark_safe("<img src='{}' />".format(escape(obj.thumbnail_url)))
    thumb.allow_tags = True


# ==== ADMIN PARA PRESTEC ====
class PrestecAdmin(admin.ModelAdmin):
    readonly_fields = ('data_prestec',)
    fields = ('exemplar', 'usuari', 'data_prestec', 'data_retorn', 'anotacions')
    list_display = ('exemplar', 'usuari', 'data_prestec', 'data_retorn')


# ==== ADMIN PARA RESERVA ====
class ReservaAdmin(admin.ModelAdmin):
    readonly_fields = ('data',)
    fields = ('exemplar', 'usuari', 'data')
    list_display = ('exemplar', 'usuari', 'data')


# ==== REGISTRO DE MODELOS EN EL ADMIN ====
admin.site.register(Usuari, UsuariAdmin)
admin.site.register(Categoria, CategoriaAdmin)
admin.site.register(Pais)
admin.site.register(Llengua)
admin.site.register(Llibre, LlibreAdmin)
admin.site.register(Revista)
admin.site.register(Dispositiu)
admin.site.register(Imatge)
admin.site.register(Centre)
admin.site.register(Grup)
admin.site.register(Reserva, ReservaAdmin)
admin.site.register(Prestec, PrestecAdmin)
admin.site.register(Peticio)
