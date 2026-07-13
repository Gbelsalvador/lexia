(function () {
    const app = document.getElementById("chat-app");
    if (!app) {
        return;
    }

    const form = document.getElementById("chat-form");
    const input = document.getElementById("chat-input");
    const submitButton = document.getElementById("chat-submit");
    const messagesContainer = document.getElementById("chat-messages");
    const loadingIndicator = document.getElementById("chat-loading");
    const errorBox = document.getElementById("chat-error");

    // Récupération des URLs depuis le DOM
    const envoyerUrl = app.dataset.envoyerUrl;
    const feedbackUrl = app.dataset.feedbackUrl;
    const analyserUrl = app.dataset.analyserUrl; // Ajout de l'URL d'analyse

    // Récupération des nouveaux éléments d'interface pour les documents
    const fileInput = document.getElementById("contract-file-input");
    const btnTriggerUpload = document.getElementById("btn-trigger-upload");
    const contractPreview = document.getElementById("contract-preview");
    const contractPreviewName = document.getElementById("contract-preview-name");
    const btnRemoveContract = document.getElementById("btn-remove-contract");

    let conversationId = app.dataset.conversationId || "";

    if (new URLSearchParams(window.location.search).get("nouveau") === "1") {
        conversationId = "";
    }

    const getCookie = (name) => {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) {
            return parts.pop().split(";").shift();
        }
        return "";
    };

    const csrfToken = getCookie("csrftoken");

    const scrollToBottom = () => {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    };

    const escapeHtml = (unsafe) => {
        return unsafe
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#039;");
    };

    const formatArticleLabel = (numeroArticle) => {
        const value = String(numeroArticle || "").trim();
        if (!value) {
            return "Article non precise";
        }
        if (value.toLowerCase().startsWith("article")) {
            return value;
        }
        return `Article ${value}`;
    };

    // Gestion de l'UI d'upload de contrat
    if (btnTriggerUpload && fileInput) {
        btnTriggerUpload.addEventListener("click", () => fileInput.click());

        fileInput.addEventListener("change", function () {
            if (this.files && this.files[0]) {
                contractPreviewName.textContent = `📄 Contrat : ${this.files[0].name}`;
                contractPreview.classList.remove("d-none");
                input.placeholder = "Ajoutez une question sur ce contrat (optionnel)...";
                input.required = false; // Permet l'envoi du document sans texte obligatoire
            }
        });
    }

    if (btnRemoveContract && fileInput) {
        btnRemoveContract.addEventListener("click", function () {
            fileInput.value = "";
            contractPreview.classList.add("d-none");
            contractPreviewName.textContent = "";
            input.placeholder = "Posez une question ou analysez un contrat avec le trombone...";
            input.required = true;
        });
    }

    // Génération enrichie de la bulle avec gestion des "points" d'analyse de contrat
    const createMessageBubble = ({ role, content, sources = [], points = [], messageId = null }) => {
        const row = document.createElement("div");
        row.className = `chat-message ${
            role === "user" ? "chat-message-user" : "chat-message-assistant"
        }`;

        const avatar = document.createElement("div");
        avatar.className = "chat-avatar";
        avatar.setAttribute("aria-hidden", "true");
        avatar.textContent = role === "user" ? "V" : "LX";

        const article = document.createElement("article");
        article.className = `chat-bubble ${
            role === "user" ? "chat-bubble-user" : "chat-bubble-assistant"
        }`;

        const contentDiv = document.createElement("div");
        contentDiv.className = "chat-bubble-content";
        contentDiv.innerHTML = escapeHtml(content).replaceAll("\n", "<br>");
        article.appendChild(contentDiv);

        if (role === "assistant") {
            // Affichage de l'analyse point par point si présente
            if (Array.isArray(points) && points.length > 0) {
                const decompositionDiv = document.createElement("div");
                decompositionDiv.className = "contract-decomposition mt-3 pt-2 border-top";
                decompositionDiv.innerHTML = '<h5 class="small text-muted mb-2">🔎 Décomposition de l\'analyse par point :</h5>';

                points.forEach((p) => {
                    const details = document.createElement("details");
                    details.className = "mb-2 bg-white border rounded p-2";
                    
                    const summary = document.createElement("summary");
                    summary.className = "fw-bold text-dark small";
                    summary.style.cursor = "pointer";
                    summary.textContent = p.titre || "Point analysé";
                    
                    const pContent = document.createElement("div");
                    pContent.className = "mt-2 text-muted small px-2 border-start";
                    pContent.innerHTML = escapeHtml(p.resume || "").replaceAll("\n", "<br>");

                    details.appendChild(summary);
                    details.appendChild(pContent);
                    decompositionDiv.appendChild(details);
                });
                article.appendChild(decompositionDiv);
            }

            // Gestion des sources citées
            if (Array.isArray(sources) && sources.length > 0) {
                const sourcesDiv = document.createElement("div");
                sourcesDiv.className = "chat-sources";
                sourcesDiv.innerHTML = '<span class="chat-sources-label">Sources citees</span>';

                sources.forEach((source) => {
                    const badge = document.createElement("span");
                    badge.className = "chat-source-badge";
                    badge.textContent = formatArticleLabel(source.numero_article);
                    sourcesDiv.appendChild(badge);
                });
                article.appendChild(sourcesDiv);
            }

            // Gestion des feedbacks
            if (messageId) {
                const feedbackDiv = document.createElement("div");
                feedbackDiv.className = "chat-feedback";
                feedbackDiv.dataset.feedbackMessageId = String(messageId);
                feedbackDiv.innerHTML = [
                    '<span class="chat-feedback-label">Utile ?</span>',
                    '<button type="button" class="btn btn-sm btn-outline-success" data-feedback="POSITIF" title="Reponse utile">👍</button>',
                    '<button type="button" class="btn btn-sm btn-outline-danger" data-feedback="NEGATIF" title="Reponse inutile">👎</button>',
                ].join("");
                article.appendChild(feedbackDiv);
            }
        }

        row.appendChild(avatar);
        row.appendChild(article);
        return row;
    };

    const setLoading = (isLoading) => {
        loadingIndicator.classList.toggle("d-none", !isLoading);
        submitButton.disabled = isLoading;
        input.disabled = isLoading;
    };

    const showError = (message) => {
        errorBox.textContent = message;
        errorBox.classList.remove("d-none");
    };

    const clearError = () => {
        errorBox.textContent = "";
        errorBox.classList.add("d-none");
    };

    // Fonction d'envoi JSON d'origine (Garde sa structure stricte)
    const postJson = async (url, body) => {
        const response = await fetch(url, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": csrfToken,
            },
            body: JSON.stringify(body),
        });

        let payload = {};
        try {
            payload = await response.json();
        } catch (error) {
            payload = {};
        }

        if (!response.ok) {
            const erreur = payload.erreur || "Erreur reseau, veuillez reessayer.";
            throw new Error(erreur);
        }

        return payload;
    };

    // Nouvelle fonction dédiée à la soumission Multipart (Fichier + Texte)
    const postMultipart = async (url, formData) => {
        const response = await fetch(url, {
            method: "POST",
            headers: {
                "X-CSRFToken": csrfToken, // Le navigateur injecte automatiquement le Content-Type avec le boundary approprié
            },
            body: formData,
        });

        let payload = {};
        try {
            payload = await response.json();
        } catch (error) {
            payload = {};
        }

        if (!response.ok) {
            const erreur = payload.erreur || "Erreur lors de l'analyse du document.";
            throw new Error(erreur);
        }

        return payload;
    };

    document.querySelectorAll(".chat-suggestion").forEach((button) => {
        button.addEventListener("click", () => {
            const question = button.dataset.question || button.textContent.trim();
            input.value = question;
            input.focus();
        });
    });

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        clearError();

        const question = input.value.trim();
        const hasFile = fileInput && fileInput.files && fileInput.files[0];

        // Validation si aucun message ni fichier n'est renseigné
        if (!question && !hasFile) {
            showError("Veuillez saisir une question ou charger un fichier.");
            return;
        }

        const emptyState = messagesContainer.querySelector(".chat-empty");
        if (emptyState) {
            emptyState.remove();
        }

        // Message affiché localement dans la bulle utilisateur
        const userDisplayContent = hasFile 
            ? `Analyse du document demandée : ${fileInput.files[0].name}${question ? `\n\nQuestion posée : ${question}` : ''}`
            : question;

        messagesContainer.appendChild(
            createMessageBubble({ role: "user", content: userDisplayContent })
        );
        scrollToBottom();

        // Stockage et réinitialisation immédiate du champ texte
        input.value = "";
        setLoading(true);

        try {
            let result;

            if (hasFile) {
                // Création du FormData pour l'envoi de fichier vers analyser_contrat
                const formData = new FormData();
                formData.append("fichier", fileInput.files[0]);
                if (question) {
                    formData.append("question", question);
                }
                if (conversationId) {
                    formData.append("conversation_id", conversationId);
                }

                result = await postMultipart(analyserUrl, formData);
                
                // Réinitialise l'aperçu du document chargé après envoi réussi
                if (btnRemoveContract) btnRemoveContract.click();
            } else {
                // Route RAG classique en JSON pur
                result = await postJson(envoyerUrl, {
                    question,
                    conversation_id: conversationId || null,
                });
            }

            conversationId = String(result.conversation_id || conversationId || "");

            messagesContainer.appendChild(
                createMessageBubble({
                    role: "assistant",
                    content: result.reponse || "",
                    sources: result.sources || [],
                    points: result.points || [], // Prise en compte du tableau structuré
                    messageId: result.message_id || null,
                })
            );
            scrollToBottom();
        } catch (error) {
            showError(error.message || "Erreur inattendue pendant le traitement.");
        } finally {
            setLoading(false);
            input.focus();
        }
    });

    messagesContainer.addEventListener("click", async (event) => {
        const button = event.target.closest("button[data-feedback]");
        if (!button) {
            return;
        }

        const wrapper = button.closest("[data-feedback-message-id]");
        if (!wrapper) {
            return;
        }

        const messageId = Number(wrapper.dataset.feedbackMessageId || "0");
        const feedback = button.dataset.feedback;
        if (!messageId || !feedback) {
            return;
        }

        try {
            await postJson(feedbackUrl, {
                message_id: messageId,
                feedback,
            });

            wrapper.querySelectorAll("button[data-feedback]").forEach((btn) => {
                btn.disabled = true;
                if (btn === button) {
                    btn.classList.add("active");
                }
            });
        } catch (error) {
            showError(error.message || "Impossible d'enregistrer le feedback.");
        }
    });

    scrollToBottom();
})();