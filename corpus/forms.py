from django import forms
from django.conf import settings

from corpus.models import DocumentJuridique


class DocumentJuridiqueForm(forms.ModelForm):
    """Formulaire d'upload d'un document juridique PDF."""

    class Meta:
        model = DocumentJuridique
        fields = ("titre", "version", "fichier")
        widgets = {
            "titre": forms.TextInput(attrs={"class": "form-control"}),
            "version": forms.TextInput(attrs={"class": "form-control"}),
            "fichier": forms.FileInput(
                attrs={
                    "class": "form-control",
                    "accept": ".pdf,application/pdf",
                }
            ),
        }

    def clean_fichier(self):
        fichier = self.cleaned_data["fichier"]

        if fichier.size > settings.MAX_UPLOAD_SIZE_BYTES:
            raise forms.ValidationError(
                f"Le fichier ne doit pas depasser {settings.MAX_UPLOAD_SIZE_MB} Mo."
            )

        if not fichier.name.lower().endswith(".pdf"):
            raise forms.ValidationError("Veuillez uploader un fichier PDF.")

        content_type = getattr(fichier, "content_type", "")
        if content_type and content_type != "application/pdf":
            raise forms.ValidationError("Le fichier doit etre un PDF valide.")

        position = fichier.tell()
        signature = fichier.read(4)
        fichier.seek(position)
        if signature != b"%PDF":
            raise forms.ValidationError("Le contenu du fichier ne semble pas etre un PDF.")

        return fichier
