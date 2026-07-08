from __future__ import annotations

import logging
import threading

from django.db import close_old_connections

logger = logging.getLogger(__name__)


def _run_indexing(document_id: int) -> None:
    """Execute l'indexation d'un document en arriere-plan."""
    close_old_connections()

    from corpus.models import DocumentJuridique
    from corpus.services import index_chunks

    try:
        document = DocumentJuridique.objects.get(pk=document_id)
        nombre_chunks = index_chunks(document)
        logger.info(
            "Indexation terminee pour document=%s (%s chunks).",
            document_id,
            nombre_chunks,
        )
    except DocumentJuridique.DoesNotExist:
        logger.warning("Document %s introuvable pour indexation asynchrone.", document_id)
    except Exception:
        logger.exception("Echec indexation asynchrone du document %s", document_id)
        DocumentJuridique.objects.filter(pk=document_id).update(
            statut=DocumentJuridique.Statut.ERREUR,
        )
    finally:
        close_old_connections()


def schedule_indexing(document_id: int) -> None:
    """Lance l'indexation dans un thread daemon pour ne pas bloquer la requete HTTP."""
    thread = threading.Thread(
        target=_run_indexing,
        args=(document_id,),
        daemon=True,
        name=f"index-doc-{document_id}",
    )
    thread.start()
