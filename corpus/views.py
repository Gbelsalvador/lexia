from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from accounts.decorators import admin_required
from corpus.forms import DocumentJuridiqueForm
from corpus.indexing import schedule_indexing
from corpus.models import DocumentJuridique


@admin_required
@require_http_methods(["GET", "POST"])
def upload_document(request):
    """Upload un PDF juridique et lance son indexation en arriere-plan."""
    if request.method == "POST":
        form = DocumentJuridiqueForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            document.uploade_par = request.user
            document.statut = DocumentJuridique.Statut.EN_COURS
            document.save()
            schedule_indexing(document.pk)
            messages.success(
                request,
                "Document enregistre. L'indexation est en cours en arriere-plan.",
            )
            return redirect("corpus:liste_documents")
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
    indexation_en_cours = documents.filter(
        statut=DocumentJuridique.Statut.EN_COURS,
    ).exists()
    return render(
        request,
        "corpus/liste_documents.html",
        {
            "documents": documents,
            "indexation_en_cours": indexation_en_cours,
        },
    )
