const state = {
  currentTicket: null,
  currentDraft: null,
};

const elements = {
  apiStatus: document.querySelector("#apiStatus"),
  refreshDocsButton: document.querySelector("#refreshDocsButton"),
  seedDocsButton: document.querySelector("#seedDocsButton"),
  documentForm: document.querySelector("#documentForm"),
  documentTitle: document.querySelector("#documentTitle"),
  documentSource: document.querySelector("#documentSource"),
  documentContent: document.querySelector("#documentContent"),
  uploadForm: document.querySelector("#uploadForm"),
  documentFile: document.querySelector("#documentFile"),
  documentsList: document.querySelector("#documentsList"),
  ticketForm: document.querySelector("#ticketForm"),
  customerEmail: document.querySelector("#customerEmail"),
  ticketSubject: document.querySelector("#ticketSubject"),
  ticketBody: document.querySelector("#ticketBody"),
  generateDraftButton: document.querySelector("#generateDraftButton"),
  classificationGrid: document.querySelector("#classificationGrid"),
  ticketCategory: document.querySelector("#ticketCategory"),
  ticketPriority: document.querySelector("#ticketPriority"),
  ticketSentiment: document.querySelector("#ticketSentiment"),
  ticketSummaryBlock: document.querySelector("#ticketSummaryBlock"),
  ticketSummary: document.querySelector("#ticketSummary"),
  emptyDraftState: document.querySelector("#emptyDraftState"),
  draftContent: document.querySelector("#draftContent"),
  draftConfidence: document.querySelector("#draftConfidence"),
  draftText: document.querySelector("#draftText"),
  actionsList: document.querySelector("#actionsList"),
  citationsList: document.querySelector("#citationsList"),
  feedbackForm: document.querySelector("#feedbackForm"),
  feedbackNotes: document.querySelector("#feedbackNotes"),
  toast: document.querySelector("#toast"),
};

async function request(path, options = {}) {
  const response = await fetch(path, options);
  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json") ? await response.json() : await response.text();

  if (!response.ok) {
    const detail = typeof payload === "object" && payload !== null ? payload.detail : payload;
    throw new Error(Array.isArray(detail) ? detail.map((item) => item.msg).join(", ") : detail || "Request failed");
  }

  return payload;
}

function showToast(message, isError = false) {
  elements.toast.textContent = message;
  elements.toast.classList.toggle("error", isError);
  elements.toast.hidden = false;

  window.clearTimeout(showToast.timeoutId);
  showToast.timeoutId = window.setTimeout(() => {
    elements.toast.hidden = true;
  }, 3200);
}

function setBusy(button, busyText) {
  const originalText = button.textContent;
  button.disabled = true;
  button.textContent = busyText;
  return () => {
    button.disabled = false;
    button.textContent = originalText;
  };
}

function textOrDash(value) {
  return value && String(value).trim() ? value : "-";
}

async function checkHealth() {
  try {
    await request("/health");
    elements.apiStatus.textContent = "API Online";
    elements.apiStatus.className = "status-pill ok";
  } catch (error) {
    elements.apiStatus.textContent = "API Offline";
    elements.apiStatus.className = "status-pill error";
  }
}

async function loadDocuments() {
  elements.documentsList.innerHTML = "<div class=\"empty-state\">Loading documents...</div>";
  try {
    const documents = await request("/documents");
    renderDocuments(documents);
  } catch (error) {
    elements.documentsList.innerHTML = "<div class=\"empty-state\">Could not load documents.</div>";
    showToast(error.message, true);
  }
}

function renderDocuments(documents) {
  if (!documents.length) {
    elements.documentsList.innerHTML = "<div class=\"empty-state\">No documents yet.</div>";
    return;
  }

  elements.documentsList.innerHTML = documents
    .map(
      (document) => `
        <article class="document-item">
          <strong>${escapeHtml(document.title)}</strong>
          <span>${escapeHtml(textOrDash(document.source_name))}</span>
          <span>${document.chunk_count} chunk${document.chunk_count === 1 ? "" : "s"}</span>
        </article>
      `,
    )
    .join("");
}

async function seedDocuments() {
  const restore = setBusy(elements.seedDocsButton, "Seeding...");
  try {
    const result = await request("/dev/seed-sample-data", { method: "POST" });
    const skipped = result.documents_skipped || 0;
    showToast(`Seeded ${result.documents_created} sample docs, skipped ${skipped}`);
    await loadDocuments();
  } catch (error) {
    showToast(error.message, true);
  } finally {
    restore();
  }
}

async function addDocument(event) {
  event.preventDefault();
  const restore = setBusy(event.submitter, "Adding...");

  try {
    await request("/documents", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: elements.documentTitle.value,
        source_name: elements.documentSource.value || null,
        content: elements.documentContent.value,
      }),
    });

    elements.documentForm.reset();
    showToast("Document added");
    await loadDocuments();
  } catch (error) {
    showToast(error.message, true);
  } finally {
    restore();
  }
}

async function uploadDocument(event) {
  event.preventDefault();
  const file = elements.documentFile.files[0];
  if (!file) {
    showToast("Choose a .txt or .md file first", true);
    return;
  }

  const restore = setBusy(event.submitter, "Uploading...");
  const formData = new FormData();
  formData.append("file", file);

  try {
    await request("/documents/upload", {
      method: "POST",
      body: formData,
    });
    elements.uploadForm.reset();
    showToast("Document uploaded");
    await loadDocuments();
  } catch (error) {
    showToast(error.message, true);
  } finally {
    restore();
  }
}

async function createTicket(event) {
  event.preventDefault();
  const restore = setBusy(event.submitter, "Creating...");

  try {
    const ticket = await request("/tickets", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        customer_email: elements.customerEmail.value || null,
        subject: elements.ticketSubject.value,
        body: elements.ticketBody.value,
      }),
    });

    state.currentTicket = ticket;
    state.currentDraft = null;
    renderTicket(ticket);
    clearDraft();
    elements.generateDraftButton.disabled = false;
    showToast(`Ticket ${ticket.id} created`);
  } catch (error) {
    showToast(error.message, true);
  } finally {
    restore();
  }
}

function renderTicket(ticket) {
  elements.classificationGrid.hidden = false;
  elements.ticketSummaryBlock.hidden = false;
  elements.ticketCategory.textContent = textOrDash(ticket.category);
  elements.ticketPriority.textContent = textOrDash(ticket.priority);
  elements.ticketSentiment.textContent = textOrDash(ticket.sentiment);
  elements.ticketSummary.textContent = textOrDash(ticket.summary);
}

async function generateDraft() {
  if (!state.currentTicket) {
    showToast("Create a ticket first", true);
    return;
  }

  const restore = setBusy(elements.generateDraftButton, "Generating...");

  try {
    const draft = await request(`/tickets/${state.currentTicket.id}/draft`, { method: "POST" });
    state.currentDraft = draft;
    renderDraft(draft);
    showToast(`Draft ${draft.id} generated`);
  } catch (error) {
    showToast(error.message, true);
  } finally {
    restore();
  }
}

function renderDraft(draft) {
  elements.emptyDraftState.hidden = true;
  elements.draftContent.hidden = false;
  elements.draftConfidence.hidden = false;
  elements.draftConfidence.textContent = `${draft.confidence}% confidence`;
  elements.draftText.value = draft.content;

  elements.actionsList.innerHTML = draft.actions.length
    ? draft.actions.map((action) => `<li>${escapeHtml(action)}</li>`).join("")
    : "<li>No suggested actions returned.</li>";

  elements.citationsList.innerHTML = draft.citations.length
    ? draft.citations
        .map(
          (citation) => `
            <article class="citation-item">
              <strong>${escapeHtml(citation.title)}</strong>
              <span>Document ${citation.document_id}, chunk ${citation.chunk_id}</span>
              <span>${escapeHtml(textOrDash(citation.source_name))}</span>
              <p>${escapeHtml(citation.excerpt)}</p>
            </article>
          `,
        )
        .join("")
    : "<div class=\"empty-state\">No citations returned.</div>";
}

function clearDraft() {
  elements.emptyDraftState.hidden = false;
  elements.draftContent.hidden = true;
  elements.draftConfidence.hidden = true;
  elements.draftText.value = "";
  elements.actionsList.innerHTML = "";
  elements.citationsList.innerHTML = "";
  elements.feedbackNotes.value = "";
}

async function saveFeedback(event) {
  event.preventDefault();
  if (!state.currentDraft) {
    showToast("Generate a draft first", true);
    return;
  }

  const restore = setBusy(event.submitter, "Saving...");
  const rating = new FormData(elements.feedbackForm).get("rating");

  try {
    await request(`/drafts/${state.currentDraft.id}/feedback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        rating,
        edited_content: rating === "edited" ? elements.draftText.value : null,
        notes: elements.feedbackNotes.value || null,
      }),
    });
    showToast("Feedback saved");
  } catch (error) {
    showToast(error.message, true);
  } finally {
    restore();
  }
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

elements.refreshDocsButton.addEventListener("click", loadDocuments);
elements.seedDocsButton.addEventListener("click", seedDocuments);
elements.documentForm.addEventListener("submit", addDocument);
elements.uploadForm.addEventListener("submit", uploadDocument);
elements.ticketForm.addEventListener("submit", createTicket);
elements.generateDraftButton.addEventListener("click", generateDraft);
elements.feedbackForm.addEventListener("submit", saveFeedback);

checkHealth();
loadDocuments();
