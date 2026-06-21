from django.contrib import admin

from corpus.models import ChunkDocument, DocumentJuridique


class ChunkDocumentInline(admin.TabularInline):
    model = ChunkDocument
    extra = 0
    fields = ("chunk_index", "numero_article", "vector_id")
    readonly_fields = ("chunk_index", "numero_article", "vector_id")
    can_delete = False


@admin.register(DocumentJuridique)
class DocumentJuridiqueAdmin(admin.ModelAdmin):
    list_display = ("titre", "version", "statut", "date_ajout", "uploade_par")
    list_filter = ("statut", "date_ajout")
    search_fields = ("titre", "version")
    readonly_fields = ("date_ajout",)
    inlines = [ChunkDocumentInline]


@admin.register(ChunkDocument)
class ChunkDocumentAdmin(admin.ModelAdmin):
    list_display = ("document", "numero_article", "chunk_index", "vector_id")
    list_filter = ("document", "numero_article")
    search_fields = ("contenu_texte", "vector_id", "numero_article")
    readonly_fields = ("document", "contenu_texte", "numero_article", "chunk_index", "vector_id")
