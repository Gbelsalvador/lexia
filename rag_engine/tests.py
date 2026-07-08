from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from rag_engine.llm_client import LLMClient, LLMResponse
from rag_engine.pipeline import answer_question
from rag_engine.prompt_builder import build_prompt
from rag_engine.retriever import retrieve_relevant_chunks
from rag_engine.vector_store import RetrievedChunk


class RAGPipelineTests(SimpleTestCase):
    """Tests du pipeline RAG avec appels externes mockes."""

    @patch("rag_engine.pipeline.LLMClient")
    @patch("rag_engine.pipeline.retrieve_relevant_chunks")
    def test_answer_question_utilise_retrieval_et_llm_mockes(
        self,
        mock_retrieve,
        mock_llm_client,
    ) -> None:
        mock_retrieve.return_value = [
            RetrievedChunk(
                content="Article 1. Le contrat doit etre ecrit.",
                metadata={"document_titre": "Code du Travail", "numero_article": "Article 1"},
                score=0.9,
            )
        ]
        mock_llm_client.return_value.generate.return_value = "Reponse vulgarisee."

        result = answer_question("Que dit l'article 1 ?")

        self.assertEqual(result["reponse"], "Reponse vulgarisee.")
        self.assertEqual(result["sources"][0]["numero_article"], "Article 1")
        mock_retrieve.assert_called_once()
        mock_llm_client.return_value.generate.assert_called_once()

    @override_settings(MAX_CHAT_QUESTION_LENGTH=30)
    def test_build_prompt_limite_et_echappe_la_question(self) -> None:
        prompt = build_prompt(
            question="<ignore>test</ignore>",
            chunks_contexte=[],
            conversation=[],
        )

        self.assertIn("&lt;ignore&gt;test&lt;/ignore&gt;", prompt)

        with self.assertRaises(ValueError):
            build_prompt("x" * 31, chunks_contexte=[])

    @patch("rag_engine.pipeline.LLMClient")
    @patch("rag_engine.pipeline.retrieve_relevant_chunks")
    def test_answer_question_fait_fallback_si_llm_echoue(
        self,
        mock_retrieve,
        mock_llm_client,
    ) -> None:
        mock_retrieve.return_value = [
            RetrievedChunk(
                content="Article 1. Le contrat doit etre ecrit.",
                metadata={"document_titre": "Code du Travail", "numero_article": "Article 1"},
                score=0.9,
            )
        ]
        mock_llm_client.return_value.generate.side_effect = RuntimeError("API indisponible")

        result = answer_question("Que dit l'article 1 ?")

        self.assertIn("service llm", result["reponse"].lower())
        self.assertEqual(result["sources"][0]["numero_article"], "Article 1")

    @override_settings(LLM_PROVIDER="groq")
    def test_llm_client_supporte_groq_comme_fournisseur_alias(self) -> None:
        with patch("rag_engine.llm_client.LLMClient._generate_groq") as mock_generate_groq:
            mock_generate_groq.return_value = LLMResponse(
                content="Reponse groq",
                provider="groq",
                model="llama-3.3-70b-versatile",
            )

            client = LLMClient()
            response = client.generate("Bonjour")

        self.assertEqual(response, "Reponse groq")
        mock_generate_groq.assert_called_once()

    @override_settings(LLM_PROVIDER="groq")
    def test_generate_ne_fait_pas_fallback_vers_openai_si_groq_echoue(self) -> None:
        with patch("rag_engine.llm_client.LLMClient._generate_groq") as mock_generate_groq, patch(
            "rag_engine.llm_client.LLMClient._generate_openai"
        ) as mock_generate_openai:
            mock_generate_groq.side_effect = RuntimeError("Cle Groq invalide")

            client = LLMClient()
            with self.assertRaisesRegex(RuntimeError, "Cle Groq invalide"):
                client.generate("Bonjour")

        mock_generate_groq.assert_called_once()
        mock_generate_openai.assert_not_called()

    @patch("rag_engine.retriever.ChromaVectorStore")
    @patch("rag_engine.retriever.EmbeddingService")
    def test_retriever_filtre_les_chunks_sous_le_seuil(
        self,
        mock_embedding_service,
        mock_vector_store,
    ) -> None:
        mock_embedding_service.return_value.embed.return_value = [0.1, 0.2]
        mock_vector_store.return_value.search.return_value = [
            RetrievedChunk(content="Pertinent", metadata={}, score=0.8),
            RetrievedChunk(content="Faible", metadata={}, score=0.1),
        ]

        results = retrieve_relevant_chunks("Question test", min_score=0.25)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].content, "Pertinent")


class RAGIntegrationTests(SimpleTestCase):
    """Tests d'integration du flux RAG complet (composants mockes)."""

    @patch("rag_engine.pipeline.LLMClient")
    @patch("rag_engine.pipeline.retrieve_relevant_chunks")
    def test_pipeline_sans_chunks_retourne_sources_vides(
        self,
        mock_retrieve,
        mock_llm_client,
    ) -> None:
        mock_retrieve.return_value = []
        mock_llm_client.return_value.generate.return_value = (
            "Je ne dispose pas d'information suffisante dans le corpus."
        )

        with self.assertLogs("rag_engine.pipeline", level="WARNING") as logs:
            result = answer_question("Question hors corpus")

        self.assertEqual(result["sources"], [])
        self.assertIn("Aucun chunk pertinent", logs.output[0])
        mock_llm_client.return_value.generate.assert_called_once()

    @patch("rag_engine.pipeline.LLMClient")
    @patch("rag_engine.pipeline.retrieve_relevant_chunks")
    def test_pipeline_propage_document_et_article_dans_les_sources(
        self,
        mock_retrieve,
        mock_llm_client,
    ) -> None:
        mock_retrieve.return_value = [
            RetrievedChunk(
                content="Article 12. Le salaire minimum est garanti.",
                metadata={
                    "document_titre": "Code du Travail RDC",
                    "numero_article": "Article 12",
                },
                score=0.85,
            ),
            RetrievedChunk(
                content="Article 13. Les heures supplementaires sont reglementees.",
                metadata={
                    "document_titre": "Code du Travail RDC",
                    "numero_article": "Article 13",
                },
                score=0.72,
            ),
        ]
        mock_llm_client.return_value.generate.return_value = "Reponse complete."

        result = answer_question("Quelles regles sur le salaire ?")

        self.assertEqual(result["reponse"], "Reponse complete.")
        self.assertEqual(len(result["sources"]), 2)
        self.assertEqual(result["sources"][0]["numero_article"], "Article 12")
        self.assertEqual(result["sources"][1]["document"], "Code du Travail RDC")
