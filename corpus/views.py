from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from accounts.decorators import admin_required
from corpus.forms import DocumentJuridiqueForm
from corpus.models import DocumentJuridique
from corpus.services import index_chunks


@admin_required
@require_http_methods(["GET", "POST"])
def upload_document(request):
    """Upload un PDF juridique et lance son indexation synchrone."""
    if request.method == "POST":
        form = DocumentJuridiqueForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            document.uploade_par = request.user
            document.save()

            try:
                nombre_chunks = index_chunks(document)
            except Exception as exc:
                document.statut = DocumentJuridique.Statut.ERREUR
                document.save(update_fields=["statut"])
                messages.error(
                    request,
                    f"Document enregistre, mais l'indexation a echoue: {exc}",
                )
            else:
                messages.success(
                    request,
                    f"Document indexe avec succes ({nombre_chunks} chunks).",
                )
                return redirect("corpus:liste_documents")
        else:
            messages.error(request, "Veuillez corriger les erreurs du formulaire.")
    else:
        form = DocumentJuridiqueForm()

    return render(request, "corpus/upload.html", {"form": form})


@admin_required
def liste_documents(request):
    """Affiche les documents juridiques deja ajoutes au corpus."""
    documents = (
        DocumentJuridique.objects.select_related("uploade_par")
        .prefetch_related("chunks")
        .all()
    )
    return render(
        request,
        "corpus/liste_documents.html",
        {"documents": documents},
    )
