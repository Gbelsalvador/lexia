from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from unittest.mock import patch

from accounts.models import Utilisateur
from corpus.forms import DocumentJuridiqueForm
from corpus.models import DocumentJuridique
from corpus.services import chunk_text


class ChunkingTests(SimpleTestCase):
    """Tests du decoupage en chunks."""

    def test_chunk_text_respecte_taille_et_chevauchement(self) -> None:
        texte = " ".join(f"mot{i}" for i in range(12))

        chunks = chunk_text(texte, taille_max=5, overlap=2)

        self.assertEqual(len(chunks), 4)
        self.assertLessEqual(max(len(chunk.content.split()) for chunk in chunks), 5)
        self.assertEqual(chunks[0].content.split()[-2:], chunks[1].content.split()[:2])
        self.assertEqual(chunks[1].content.split()[-2:], chunks[2].content.split()[:2])

    def test_chunk_text_detecte_les_articles_apres_normalisation(self) -> None:
        texte = (
            "Preambule du code.\n\n"
            "Article 1. Le contrat de travail est conclu par ecrit.\n\n"
            "Article 2. La duree du travail est limitee."
        )

        chunks = chunk_text(texte, taille_max=50, overlap=5)

        articles = {chunk.numero_article for chunk in chunks if chunk.numero_article}
        self.assertIn("Article 1", articles)
        self.assertIn("Article 2", articles)


class DocumentUploadValidationTests(TestCase):
    """Tests de validation des PDF uploades."""

    @override_settings(MAX_UPLOAD_SIZE_BYTES=8, MAX_UPLOAD_SIZE_MB=0)
    def test_rejette_un_pdf_trop_volumineux(self) -> None:
        fichier = SimpleUploadedFile(
            "code.pdf",
            b"%PDF-123456789",
            content_type="application/pdf",
        )

        form = DocumentJuridiqueForm(
            data={"titre": "Code", "version": "v1"},
            files={"fichier": fichier},
        )

        self.assertFalse(form.is_valid())
        self.assertIn("fichier", form.errors)

    def test_rejette_un_fichier_non_pdf(self) -> None:
        fichier = SimpleUploadedFile(
            "code.txt",
            b"not a pdf",
            content_type="text/plain",
        )

        form = DocumentJuridiqueForm(
            data={"titre": "Code", "version": "v1"},
            files={"fichier": fichier},
        )

        self.assertFalse(form.is_valid())
        self.assertIn("fichier", form.errors)


class DocumentUploadViewTests(TestCase):
    """Tests du flux d'upload avec indexation asynchrone."""

    def setUp(self) -> None:
        self.admin = Utilisateur.objects.create_user(
            username="admin_corpus",
            password="MotDePasseComplexe123!",
            role=Utilisateur.Role.ADMIN,
        )

    @patch("corpus.views.schedule_indexing")
    def test_upload_lance_indexation_asynchrone(self, mock_schedule) -> None:
        fichier = SimpleUploadedFile(
            "code.pdf",
            b"%PDF-123456789",
            content_type="application/pdf",
        )
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse("corpus:upload"),
            {
                "titre": "Code du Travail",
                "version": "v1",
                "fichier": fichier,
            },
        )

        self.assertRedirects(response, reverse("corpus:liste_documents"))
        document = DocumentJuridique.objects.get(titre="Code du Travail")
        self.assertEqual(document.statut, DocumentJuridique.Statut.EN_COURS)
        mock_schedule.assert_called_once_with(document.pk)


class IndexChunksIntegrationTests(TestCase):
    """Test d'integration chunking -> metadonnees -> stockage BDD."""

    def setUp(self) -> None:
        self.admin = Utilisateur.objects.create_user(
            username="admin_index",
            password="MotDePasseComplexe123!",
            role=Utilisateur.Role.ADMIN,
        )

    @patch("corpus.services.ChromaVectorStore")
    @patch("corpus.services.EmbeddingService")
    @patch("corpus.services.extract_text_from_pdf")
    def test_index_chunks_conserve_les_numeros_d_articles(
        self,
        mock_extract,
        mock_embedding_service,
        mock_vector_store,
    ) -> None:
        from corpus.services import index_chunks

        mock_extract.return_value = (
            "Article 1. Le contrat est ecrit.\n\n"
            "Article 2. La duree du travail est limitee."
        )
        mock_embedding_service.return_value.embed_many.return_value = [[0.1], [0.2]]
        mock_store = mock_vector_store.return_value

        fichier = SimpleUploadedFile(
            "code.pdf",
            b"%PDF-123456789",
            content_type="application/pdf",
        )
        document = DocumentJuridique.objects.create(
            titre="Code test",
            version="v1",
            fichier=fichier,
            uploade_par=self.admin,
        )

        nombre = index_chunks(document)

        self.assertEqual(nombre, 2)
        document.refresh_from_db()
        self.assertEqual(document.statut, DocumentJuridique.Statut.ACTIF)
        articles = set(document.chunks.values_list("numero_article", flat=True))
        self.assertEqual(articles, {"Article 1", "Article 2"})
        mock_store.add_chunks.assert_called_once()
        metadatas = mock_store.add_chunks.call_args.kwargs["metadatas"]
        self.assertEqual(
            {meta["numero_article"] for meta in metadatas},
            {"Article 1", "Article 2"},
        )
