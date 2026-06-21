from django import forms

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
        if not fichier.name.lower().endswith(".pdf"):
            raise forms.ValidationError("Veuillez uploader un fichier PDF.")
        return fichier
