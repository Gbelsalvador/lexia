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

    const envoyerUrl = app.dataset.envoyerUrl;
    const feedbackUrl = app.dataset.feedbackUrl;

    let conversationId = app.dataset.conversationId || "";

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
            return "Article non precise du Code du Travail";
        }

        if (value.toLowerCase().startsWith("article")) {
            return `${value} du Code du Travail`;
        }

        return `Article ${value} du Code du Travail`;
    };

    const createMessageBubble = ({ role, content, sources = [], messageId = null }) => {
        const article = document.createElement("article");
        article.className = `chat-bubble ${
            role === "user" ? "chat-bubble-user" : "chat-bubble-assistant"
        }`;

        const contentDiv = document.createElement("div");
        contentDiv.className = "chat-bubble-content";
        contentDiv.innerHTML = escapeHtml(content).replaceAll("\n", "<br>");
        article.appendChild(contentDiv);

        if (role === "assistant" && Array.isArray(sources) && sources.length > 0) {
            const sourcesDiv = document.createElement("div");
            sourcesDiv.className = "chat-sources mt-2";
            sources.forEach((source) => {
                const badge = document.createElement("span");
                badge.className = "badge text-bg-light border me-1 mb-1";
                badge.textContent = formatArticleLabel(source.numero_article);
                sourcesDiv.appendChild(badge);
            });
            article.appendChild(sourcesDiv);

            if (messageId) {
                const feedbackDiv = document.createElement("div");
                feedbackDiv.className = "chat-feedback mt-2";
                feedbackDiv.dataset.feedbackMessageId = String(messageId);
                feedbackDiv.innerHTML = [
                    '<button type="button" class="btn btn-sm btn-outline-success" data-feedback="POSITIF">👍</button>',
                    '<button type="button" class="btn btn-sm btn-outline-danger" data-feedback="NEGATIF">👎</button>',
                ].join("");
                article.appendChild(feedbackDiv);
            }
        }

        return article;
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

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        clearError();

        const question = input.value.trim();
        if (!question) {
            showError("Veuillez saisir une question.");
            return;
        }

        const emptyState = messagesContainer.querySelector(".chat-empty");
        if (emptyState) {
            emptyState.remove();
        }

        messagesContainer.appendChild(
            createMessageBubble({ role: "user", content: question })
        );
        scrollToBottom();

        input.value = "";
        setLoading(true);

        try {
            const result = await postJson(envoyerUrl, {
                question,
                conversation_id: conversationId || null,
            });

            conversationId = String(result.conversation_id || conversationId || "");

            messagesContainer.appendChild(
                createMessageBubble({
                    role: "assistant",
                    content: result.reponse || "",
                    sources: result.sources || [],
                    messageId: result.message_id || null,
                })
            );
            scrollToBottom();
        } catch (error) {
            showError(error.message || "Erreur inattendue pendant l'envoi du message.");
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
