const state = {
  currentTicket: null,
  currentDraft: null,
  feedbackSaved: false,
};

const sampleTickets = {
  billing: {
    customer_email: "customer@example.com",
    subject: "Charged twice after upgrade",
    body: "I upgraded my plan yesterday and was charged twice. Can you refund me?",
  },
  login: {
    customer_email: "customer@example.com",
    subject: "Cannot login to my account",
    body: "I cannot login and the password reset email never arrives. What should I do?",
  },
};

const elements = {
  apiStatus: document.querySelector("#apiStatus"),
  refreshDocsButton: document.querySelector("#refreshDocsButton"),
  seedDocsButton: document.querySelector("#seedDocsButton"),
  documentCount: document.querySelector("#documentCount"),
  chunkCount: document.querySelector("#chunkCount"),
  documentForm: document.querySelector("#documentForm"),
  documentTitle: document.querySelector("#documentTitle"),
  documentSource: document.querySelector("#documentSource"),
  documentContent: document.querySelector("#documentContent"),
  uploadForm: document.querySelector("#uploadForm"),
  documentFile: document.querySelector("#documentFile"),
  documentsList: document.querySelector("#documentsList"),
  billingSampleButton: document.querySelector("#billingSampleButton"),
  loginSampleButton: document.querySelector("#loginSampleButton"),
  ticketForm: document.querySelector("#ticketForm"),
  ticketState: document.querySelector("#ticketState"),
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
  draftState: document.querySelector("#draftState"),
  emptyDraftState: document.querySelector("#emptyDraftState"),
  draftContent: document.querySelector("#draftContent"),
  draftConfidence: document.querySelector("#draftConfidence"),
  draftText: document.querySelector("#draftText"),
  actionsList: document.querySelector("#actionsList"),
  citationsList: document.querySelector("#citationsList"),
  feedbackForm: document.querySelector("#feedbackForm"),
  feedbackNotes: document.querySelector("#feedbackNotes"),
  toast: document.querySelector("#toast"),
  stepDocs: document.querySelector("#stepDocs"),
  stepTicket: document.querySelector("#stepTicket"),
  stepDraft: document.querySelector("#stepDraft"),
  stepFeedback: document.querySelector("#stepFeedback"),
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

function titleCase(value) {
  return textOrDash(value)
    .split(/[\s_-]+/)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
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
  elements.documentsList.innerHTML = "<div class=\"empty-state\"><strong>Loading</strong><span>Fetching sources...</span></div>";
  try {
    const documents = await request("/documents");
    renderDocuments(documents);
    updateWorkflow();
  } catch (error) {
    elements.documentsList.innerHTML = "<div class=\"empty-state\"><strong>Unavailable</strong><span>Could not load sources.</span></div>";
    showToast(error.message, true);
  }
}

function renderDocuments(documents) {
  const totalChunks = documents.reduce((total, document) => total + document.chunk_count, 0);
  elements.documentCount.textContent = documents.length;
  elements.chunkCount.textContent = totalChunks;

  if (!documents.length) {
    elements.documentsList.innerHTML = "<div class=\"empty-state\"><strong>No sources</strong><span>Seed or add a document.</span></div>";
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
    showToast(`Sources ready: ${result.documents_created} added, ${skipped} skipped`);
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

function fillSampleTicket(type) {
  const sample = sampleTickets[type];
  elements.customerEmail.value = sample.customer_email;
  elements.ticketSubject.value = sample.subject;
  elements.ticketBody.value = sample.body;
  showToast(`${titleCase(type)} sample loaded`);
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
    state.feedbackSaved = false;
    renderTicket(ticket);
    clearDraft();
    elements.generateDraftButton.disabled = false;
    elements.ticketState.textContent = `Ticket #${ticket.id}`;
    elements.ticketState.className = "subtle-pill ready";
    showToast(`Ticket ${ticket.id} created`);
    updateWorkflow();
  } catch (error) {
    showToast(error.message, true);
  } finally {
    restore();
  }
}

function renderTicket(ticket) {
  elements.classificationGrid.hidden = false;
  elements.ticketSummaryBlock.hidden = false;
  elements.ticketCategory.textContent = titleCase(ticket.category);
  elements.ticketPriority.textContent = titleCase(ticket.priority);
  elements.ticketSentiment.textContent = titleCase(ticket.sentiment);
  elements.ticketSummary.textContent = textOrDash(ticket.summary);
}

async function generateDraft() {
  if (!state.currentTicket) {
    showToast("Create a ticket first", true);
    return;
  }

  const restore = setBusy(elements.generateDraftButton, "Generating...");
  elements.draftState.textContent = "Generating";

  try {
    const draft = await request(`/tickets/${state.currentTicket.id}/draft`, { method: "POST" });
    state.currentDraft = draft;
    state.feedbackSaved = false;
    renderDraft(draft);
    showToast(`Draft ${draft.id} generated`);
    updateWorkflow();
  } catch (error) {
    elements.draftState.textContent = "Error";
    elements.draftState.className = "subtle-pill error";
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
  elements.draftState.textContent = `Draft #${draft.id}`;
  elements.draftState.className = "subtle-pill ready";

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
    : "<div class=\"empty-state\"><strong>No citations</strong><span>No source chunks returned.</span></div>";
}

function clearDraft() {
  elements.emptyDraftState.hidden = false;
  elements.draftContent.hidden = true;
  elements.draftConfidence.hidden = true;
  elements.draftState.textContent = "Waiting";
  elements.draftState.className = "subtle-pill";
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
    state.feedbackSaved = true;
    showToast("Feedback saved");
    updateWorkflow();
  } catch (error) {
    showToast(error.message, true);
  } finally {
    restore();
  }
}

function updateWorkflow() {
  setStep(elements.stepDocs, Number(elements.documentCount.textContent) > 0, true);
  setStep(elements.stepTicket, Boolean(state.currentTicket), Number(elements.documentCount.textContent) > 0 && !state.currentTicket);
  setStep(elements.stepDraft, Boolean(state.currentDraft), Boolean(state.currentTicket) && !state.currentDraft);
  setStep(elements.stepFeedback, state.feedbackSaved, Boolean(state.currentDraft) && !state.feedbackSaved);
}

function setStep(element, done, active) {
  element.classList.toggle("done", done);
  element.classList.toggle("active", active);
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
elements.billingSampleButton.addEventListener("click", () => fillSampleTicket("billing"));
elements.loginSampleButton.addEventListener("click", () => fillSampleTicket("login"));
elements.ticketForm.addEventListener("submit", createTicket);
elements.generateDraftButton.addEventListener("click", generateDraft);
elements.feedbackForm.addEventListener("submit", saveFeedback);

checkHealth();
loadDocuments();
updateWorkflow();
