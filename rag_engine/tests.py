from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from rag_engine.pipeline import answer_question
from rag_engine.prompt_builder import build_prompt
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
