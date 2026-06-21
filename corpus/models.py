from django.conf import settings
from django.db import models
from django.utils import timezone


class DocumentJuridique(models.Model):
    """Document officiel utilise comme source du corpus juridique."""

    class Statut(models.TextChoices):
        ACTIF = "ACTIF", "Actif"
        ARCHIVE = "ARCHIVE", "Archive"
        ERREUR = "ERREUR", "Erreur d'indexation"

    titre = models.CharField(max_length=255)
    fichier = models.FileField(upload_to="documents_juridiques/")
    version = models.CharField(max_length=100, blank=True)
    date_ajout = models.DateTimeField(default=timezone.now)
    statut = models.CharField(
        max_length=20,
        choices=Statut.choices,
        default=Statut.ACTIF,
    )
    uploade_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="documents_uploades",
    )

    class Meta:
        verbose_name = "document juridique"
        verbose_name_plural = "documents juridiques"
        ordering = ["-date_ajout"]

    def __str__(self) -> str:
        return self.titre


class ChunkDocument(models.Model):
    """Fragment textuel indexe dans ChromaDB et conserve pour tracabilite."""

    document = models.ForeignKey(
        DocumentJuridique,
        on_delete=models.CASCADE,
        related_name="chunks",
    )
    contenu_texte = models.TextField()
    numero_article = models.CharField(max_length=50, blank=True, null=True)
    chunk_index = models.PositiveIntegerField()
    vector_id = models.CharField(
        max_length=255,
        unique=True,
        help_text="Identifiant du vecteur correspondant dans ChromaDB.",
    )

    class Meta:
        verbose_name = "chunk de document"
        verbose_name_plural = "chunks de document"
        ordering = ["document", "chunk_index"]
        constraints = [
            models.UniqueConstraint(
                fields=["document", "chunk_index"],
                name="unique_chunk_index_par_document",
            )
        ]

    def __str__(self) -> str:
        article = self.numero_article or "sans article"
        return f"{self.document.titre} - {article} - chunk {self.chunk_index}"
