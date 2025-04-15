from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import escape, mark_safe
from django.forms.models import BaseInlineFormSet
from django.core.exceptions import ObjectDoesNotExist
from django import forms
from django.utils.safestring import mark_safe

from .models import (
    Categoria, Pais, Llengua, Llibre, Exemplar, Usuari, Prestec, Reserva,
    Centre, Grup, Revista, CD, DVD, BR, Dispositiu, Imatge, Autor, Editorial, Peticio
)

# ============================
# Widgets personalizados usando HTML5 datalist
# ============================
class AutorWidget(forms.TextInput):
    def format_value(self, value):
        # Si ya es una cadena, retornarla
        if isinstance(value, str):
            return value
        # Si es una instancia de Autor, retorna su nombre
        if isinstance(value, Autor):
            return value.nom
        # Si se recibe un valor (por ejemplo, pk), se intenta obtener la instancia
        if value:
            try:
                autor = Autor.objects.get(pk=value)
                return autor.nom
            except (Autor.DoesNotExist, ValueError, TypeError):
                return value
        return ''

    def render(self, name, value, attrs=None, renderer=None):
        # El valor ya se formateó en format_value, así que procedemos a renderizar
        html = super().render(name, value, attrs, renderer)
        # Genera el datalist con todos los autores existentes
        options = ''.join(f'<option value="{autor.nom}">' for autor in Autor.objects.all())
        datalist = f'<datalist id="autors_list">{options}</datalist>'
        return mark_safe(html + datalist)

class EditorialWidget(forms.TextInput):
    def format_value(self, value):
        if isinstance(value, str):
            return value
        if isinstance(value, Editorial):
            return value.nom
        if value:
            try:
                editorial = Editorial.objects.get(pk=value)
                return editorial.nom
            except (Editorial.DoesNotExist, ValueError, TypeError):
                return value
        return ''

    def render(self, name, value, attrs=None, renderer=None):
        html = super().render(name, value, attrs, renderer)
        options = ''.join(f'<option value="{edi.nom}">' for edi in Editorial.objects.all())
        datalist = f'<datalist id="editorials_list">{options}</datalist>'
        return mark_safe(html + datalist)

# ============================
# Formulario personalizado para Llibre
# ============================
class LlibreForm(forms.ModelForm):
    autor = forms.CharField(
        widget=AutorWidget(attrs={'list': 'autors_list', 'placeholder': 'Escribe el autor...'})
    )
    editorial = forms.CharField(
        widget=EditorialWidget(attrs={'list': 'editorials_list', 'placeholder': 'Escribe la editorial...'})
    )

    class Meta:
        model = Llibre
        fields = '__all__'

    def clean_autor(self):
        autor_nom = self.cleaned_data['autor'].strip()
        if autor_nom:
            autor, created = Autor.objects.get_or_create(nom=autor_nom)
            return autor
        return None

    def clean_editorial(self):
        editorial_nom = self.cleaned_data['editorial'].strip()
        if editorial_nom:
            editorial, created = Editorial.objects.get_or_create(nom=editorial_nom)
            return editorial
        return None

# ============================
# ADMIN PARA CATEGORIA
# ============================
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nom', 'parent')
    ordering = ('parent', 'nom')

# ============================
# ADMIN PARA USUARI
# ============================
class UsuariAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Dades acadèmiques", {
            'fields': ('centre', 'grup', 'imatge', 'telefon'),
        }),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {
            'fields': ('telefon',),
        }),
    )
    list_display = UserAdmin.list_display + ('telefon',)

# ============================
# INLINE PARA EXEMPLARS (EJEMPLARES)
# ============================
class ExemplarInlineFormSet(BaseInlineFormSet):
    def save_new(self, form, commit=True):
        instance = super().save_new(form, commit=False)
        if not instance.centre and hasattr(self, 'request') and self.request.user.centre:
            instance.centre = self.request.user.centre
        if commit:
            instance.save()
        return instance

    def save_existing(self, form, instance, commit=True):
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
        if not request.user.is_superuser:
            if request.user.centre:
                return qs.filter(centre=request.user.centre)
            return qs.none()
        return qs

    def get_readonly_fields(self, request, obj=None):
        if not request.user.is_superuser:
            return self.readonly_fields + ('centre',)
        return self.readonly_fields

# ============================
# ADMIN PARA LLIBRE
# ============================
class LlibreAdmin(admin.ModelAdmin):
    form = LlibreForm
    change_form_template = 'admin/change_form.html'
    filter_horizontal = ('tags',)
    inlines = [ExemplarsInline,]
    search_fields = ('titol', 'CDU', 'signatura', 'ISBN', 'colleccio')
    list_display = ('titol', 'autor', 'editorial', 'num_exemplars')
    readonly_fields = ('thumb',)

    def num_exemplars(self, obj):
        return obj.exemplar_set.count()

    def thumb(self, obj):
        return mark_safe("<img src='{}' />".format(escape(obj.thumbnail_url)))
    thumb.allow_tags = True

# ============================
# ADMIN PARA PRESTEC
# ============================
class PrestecAdmin(admin.ModelAdmin):
    readonly_fields = ('data_prestec',)
    fields = ('exemplar', 'usuari', 'data_prestec', 'data_retorn', 'anotacions')
    list_display = ('exemplar', 'usuari', 'data_prestec', 'data_retorn')

# ============================
# ADMIN PARA RESERVA
# ============================
class ReservaAdmin(admin.ModelAdmin):
    readonly_fields = ('data',)
    fields = ('exemplar', 'usuari', 'data')
    list_display = ('exemplar', 'usuari', 'data')

# ============================
# REGISTRO DE MODELOS EN EL ADMIN
# ============================
@admin.register(Autor)
class AutorAdmin(admin.ModelAdmin):
    search_fields = ['nom']

@admin.register(Editorial)
class EditorialAdmin(admin.ModelAdmin):
    search_fields = ['nom']

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
