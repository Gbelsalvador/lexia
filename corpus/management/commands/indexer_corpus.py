from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError

from corpus.models import DocumentJuridique
from corpus.services import index_chunks


class Command(BaseCommand):
    help = "Indexe un PDF juridique dans le corpus et ChromaDB."

    def add_arguments(self, parser) -> None:
        parser.add_argument("pdf_path", type=str, help="Chemin vers le PDF a indexer.")
        parser.add_argument(
            "--titre",
            type=str,
            default="Code du Travail",
            help="Titre du document juridique.",
        )
        parser.add_argument(
            "--version",
            type=str,
            default="",
            help="Version ou reference du document.",
        )
        parser.add_argument(
            "--username",
            type=str,
            default="admin",
            help="Utilisateur admin associe a l'upload.",
        )

    def handle(self, *args, **options) -> None:
        pdf_path = Path(options["pdf_path"]).resolve()
        if not pdf_path.exists():
            raise CommandError(f"Fichier introuvable: {pdf_path}")
        if pdf_path.suffix.lower() != ".pdf":
            raise CommandError("Le fichier fourni doit etre un PDF.")

        User = get_user_model()
        user, created = User.objects.get_or_create(
            username=options["username"],
            defaults={
                "email": "",
                "role": "ADMIN",
                "is_staff": True,
            },
        )
        if created:
            user.set_unusable_password()
            user.save()

        with pdf_path.open("rb") as opened_file:
            document = DocumentJuridique.objects.create(
                titre=options["titre"],
                version=options["version"],
                fichier=File(opened_file, name=pdf_path.name),
                uploade_par=user,
            )

        try:
            count = index_chunks(document)
        except Exception as exc:
            document.statut = DocumentJuridique.Statut.ERREUR
            document.save(update_fields=["statut"])
            raise CommandError(f"Indexation echouee: {exc}") from exc

        self.stdout.write(
            self.style.SUCCESS(
                f"Document indexe avec succes: {document.titre} ({count} chunks)."
            )
        )
