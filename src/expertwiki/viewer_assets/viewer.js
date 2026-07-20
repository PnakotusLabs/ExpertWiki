"use strict";

const state = {
  kind: "draft",
  documents: { draft: [], approved: [], rejected: [], published: [] },
  selectedId: null,
  pendingActionId: null,
  removingActionId: null,
  graph: null,
  graphLoaded: false,
};

const elements = {
  bundleTitle: document.getElementById("bundle-title"),
  bundleRoot: document.getElementById("bundle-root"),
  sourceCount: document.getElementById("source-count"),
  draftCount: document.getElementById("draft-count"),
  approvedCount: document.getElementById("approved-count"),
  publishedCount: document.getElementById("published-count"),
  rejectedCount: document.getElementById("rejected-count"),
  draftTabCount: document.getElementById("draft-tab-count"),
  approvedTabCount: document.getElementById("approved-tab-count"),
  publishedTabCount: document.getElementById("published-tab-count"),
  rejectedTabCount: document.getElementById("rejected-tab-count"),
  resultCount: document.getElementById("result-count"),
  documentSearch: document.getElementById("document-search"),
  documentList: document.getElementById("document-list"),
  readerEmpty: document.getElementById("reader-empty"),
  readerContent: document.getElementById("reader-content"),
  documentStatus: document.getElementById("document-status"),
  documentType: document.getElementById("document-type"),
  documentTitle: document.getElementById("document-title"),
  documentDescription: document.getElementById("document-description"),
  documentTags: document.getElementById("document-tags"),
  markdownBody: document.getElementById("markdown-body"),
  evidenceTitle: document.getElementById("evidence-title"),
  evidenceRange: document.getElementById("evidence-range"),
  evidenceEmpty: document.getElementById("evidence-empty"),
  evidenceContent: document.getElementById("evidence-content"),
  evidencePath: document.getElementById("evidence-path"),
  sourceLines: document.getElementById("source-lines"),
  libraryView: document.getElementById("library-view"),
  graphView: document.getElementById("graph-view"),
  graphSearch: document.getElementById("graph-search"),
  graphCanvas: document.getElementById("graph-canvas"),
  graphLoading: document.getElementById("graph-loading"),
  graphConceptCount: document.getElementById("graph-concept-count"),
  graphSourceCount: document.getElementById("graph-source-count"),
  graphEdgeCount: document.getElementById("graph-edge-count"),
  graphSelection: document.getElementById("graph-selection"),
  fitGraph: document.getElementById("fit-graph"),
};

document.addEventListener("DOMContentLoaded", initialize);

async function initialize() {
  bindControls();
  try {
    const summary = await fetchJson("/api/summary");
    renderSummary(summary);
    await loadAllDocuments();
    renderDocumentList();
    const first = state.documents.draft[0];
    if (first) {
      await openDocument("draft", first.id);
    }
  } catch (error) {
    showFatalError(error);
  }
}

function bindControls() {
  document.querySelectorAll(".tab-button").forEach((button) => {
    button.addEventListener("click", () => switchPrimaryView(button.dataset.view));
  });
  document.querySelectorAll(".segment").forEach((button) => {
    button.addEventListener("click", () => switchDocumentKind(button.dataset.kind));
  });
  elements.documentSearch.addEventListener("input", renderDocumentList);
  elements.graphSearch.addEventListener("input", searchGraph);
  elements.fitGraph.addEventListener("click", resetGraphView);
}

function renderSummary(summary) {
  document.title = `${summary.title} · ExpertWiki`;
  elements.bundleTitle.textContent = summary.title;
  elements.bundleRoot.textContent = summary.root;
  elements.sourceCount.textContent = summary.source_count;
  elements.draftCount.textContent = summary.draft_count;
  elements.approvedCount.textContent = summary.approved_count;
  elements.publishedCount.textContent = summary.published_count;
  elements.rejectedCount.textContent = summary.rejected_count;
  elements.draftTabCount.textContent = summary.draft_count;
  elements.approvedTabCount.textContent = summary.approved_count;
  elements.publishedTabCount.textContent = summary.published_count;
  elements.rejectedTabCount.textContent = summary.rejected_count;
}

async function loadDocuments(kind) {
  const response = await fetchJson(`/api/documents?kind=${encodeURIComponent(kind)}`);
  state.documents[kind] = response.documents;
}

async function loadAllDocuments() {
  await Promise.all([
    loadDocuments("draft"),
    loadDocuments("approved"),
    loadDocuments("published"),
    loadDocuments("rejected"),
  ]);
}

async function switchDocumentKind(kind, targetId = null) {
  state.kind = kind;
  state.selectedId = null;
  document.querySelectorAll(".segment").forEach((button) => {
    button.classList.toggle("active", button.dataset.kind === kind);
  });
  renderDocumentList();
  const target = targetId
    ? state.documents[kind].find((item) => item.id === targetId)
    : filteredDocuments()[0];
  if (target) {
    await openDocument(kind, target.id);
  } else {
    clearReader(emptyReaderTitle(kind));
  }
}

function emptyReaderTitle(kind) {
  if (kind === "draft") {
    return "No pending drafts";
  }
  if (kind === "approved") {
    return "No approved pages";
  }
  if (kind === "published") {
    return "No published pages";
  }
  return "No rejected pages";
}

function filteredDocuments() {
  const query = elements.documentSearch.value.trim().toLocaleLowerCase();
  if (!query) {
    return state.documents[state.kind];
  }
  return state.documents[state.kind].filter((item) => {
    const text = [item.title, item.description, item.entity_type, ...item.tags]
      .join(" ")
      .toLocaleLowerCase();
    return text.includes(query);
  });
}

function renderDocumentList() {
  const documents = filteredDocuments();
  elements.documentList.replaceChildren();
  elements.resultCount.textContent = `${documents.length} document${documents.length === 1 ? "" : "s"}`;

  documents.forEach((item) => {
    const itemNode = document.createElement("div");
    itemNode.className = "document-item";
    itemNode.setAttribute("role", "option");
    itemNode.setAttribute("aria-selected", String(item.id === state.selectedId));
    itemNode.classList.toggle("selected", item.id === state.selectedId);
    itemNode.classList.add(`${state.kind}-item`);
    itemNode.classList.toggle(
      "has-actions",
      ["draft", "approved", "rejected"].includes(state.kind),
    );
    itemNode.classList.toggle("removing", item.id === state.removingActionId);
    itemNode.dataset.documentId = item.id;

    const openButton = document.createElement("button");
    openButton.type = "button";
    openButton.className = "document-open";
    openButton.setAttribute("aria-label", `Open ${item.title}`);

    const title = document.createElement("strong");
    title.textContent = item.title;
    const description = document.createElement("span");
    description.className = "item-description";
    description.textContent = item.description || "No description";
    const meta = document.createElement("span");
    meta.className = "item-meta";
    meta.textContent = `${item.entity_type} · ${item.sources.length} source${item.sources.length === 1 ? "" : "s"}`;
    openButton.append(title, description, meta);
    openButton.addEventListener("click", () => openDocument(state.kind, item.id));
    itemNode.append(openButton);

    if (state.kind === "draft") {
      const actions = document.createElement("div");
      actions.className = "document-actions";
      actions.append(
        documentActionButton("Approve", "approve", item.id),
        documentActionButton("Reject", "reject", item.id),
      );
      itemNode.append(actions);
    } else if (state.kind === "approved") {
      const actions = document.createElement("div");
      actions.className = "document-actions";
      actions.append(documentActionButton("Draft", "draft", item.id));
      itemNode.append(actions);
    } else if (state.kind === "rejected") {
      const actions = document.createElement("div");
      actions.className = "document-actions";
      actions.append(documentActionButton("Draft", "draft", item.id));
      itemNode.append(actions);
    }
    elements.documentList.append(itemNode);
  });
}

function documentActionButton(label, action, id) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = `document-action ${action}`;
  button.textContent = label;
  button.disabled = state.pendingActionId === id || state.removingActionId === id;
  button.addEventListener("click", async (event) => {
    event.stopPropagation();
    if (action === "approve") {
      await approveDraft(id);
    } else if (action === "reject") {
      await rejectDraft(id);
    } else if (state.kind === "approved") {
      await returnApprovedToDraft(id);
    } else {
      await returnRejectedToDraft(id);
    }
  });
  return button;
}

async function openDocument(kind, id) {
  state.kind = kind;
  state.selectedId = id;
  renderDocumentList();
  const data = await fetchJson(
    `/api/document?kind=${encodeURIComponent(kind)}&id=${encodeURIComponent(id)}`,
  );
  elements.readerEmpty.classList.add("hidden");
  elements.readerContent.classList.remove("hidden");
  elements.documentStatus.textContent = data.status.replaceAll("_", " ");
  elements.documentType.textContent = data.entity_type;
  elements.documentTitle.textContent = data.title;
  elements.documentDescription.textContent = data.description;
  elements.documentDescription.classList.toggle("hidden", !data.description);
  elements.documentTags.replaceChildren();
  data.tags.forEach((tag) => {
    const item = document.createElement("span");
    item.textContent = tag;
    elements.documentTags.append(item);
  });
  elements.documentTags.classList.toggle("hidden", data.tags.length === 0);
  renderMarkdown(data.body, data.citations);
  resetEvidence();
  document.querySelector(".reader-panel").scrollTop = 0;
}

function clearReader(title) {
  state.selectedId = null;
  elements.readerContent.classList.add("hidden");
  elements.readerEmpty.classList.remove("hidden");
  elements.readerEmpty.querySelector("strong").textContent = title;
  elements.readerEmpty.querySelector("p").textContent = "Try another view or clear the search filter.";
  resetEvidence();
}

async function approveDraft(id) {
  await runDraftAction(id, async () => postJson("/api/draft/approve", { id }));
}

async function rejectDraft(id) {
  const feedback = "Rejected from viewer.";
  await runDraftAction(id, async () => postJson("/api/draft/reject", { id, feedback }));
}

async function returnApprovedToDraft(id) {
  await runDocumentAction(id, async () => postJson("/api/approved/draft", { id }));
}

async function returnRejectedToDraft(id) {
  await runDocumentAction(id, async () => postJson("/api/rejected/draft", { id }));
}

async function runDraftAction(id, request) {
  await runDocumentAction(id, request);
}

async function runDocumentAction(id, request) {
  if (state.pendingActionId) {
    return;
  }
  state.pendingActionId = id;
  renderDocumentList();
  try {
    const result = await request();
    state.pendingActionId = null;
    state.removingActionId = id;
    renderDocumentList();
    await waitForDraftRemovalAnimation(id);
    await refreshLibraryAfterDraftAction(result);
  } catch (error) {
    window.alert(error instanceof Error ? error.message : String(error));
  } finally {
    state.pendingActionId = null;
    state.removingActionId = null;
    renderDocumentList();
  }
}

async function refreshLibraryAfterDraftAction(result) {
  renderSummary(result.summary || (await fetchJson("/api/summary")));
  await loadAllDocuments();
  invalidateGraph();
  if (result.action === "rejected" && result.rejected_id) {
    await switchDocumentKind("rejected", result.rejected_id);
    return;
  }
  if (result.action === "drafted" && result.draft_id) {
    await switchDocumentKind("draft", result.draft_id);
    return;
  }
  await switchDocumentKind("draft");
}

function waitForDraftRemovalAnimation(id) {
  const selector = `[data-document-id="${CSS.escape(id)}"]`;
  const item = elements.documentList.querySelector(selector);
  if (!item) {
    return Promise.resolve();
  }
  return new Promise((resolve) => {
    let settled = false;
    const finish = () => {
      if (settled) {
        return;
      }
      settled = true;
      item.removeEventListener("animationend", finish);
      resolve();
    };
    item.addEventListener("animationend", finish);
    window.setTimeout(finish, 360);
  });
}

function invalidateGraph() {
  state.graphLoaded = false;
  if (state.graph) {
    state.graph.destroy();
    state.graph = null;
  }
  elements.graphLoading.classList.remove("hidden");
}

function renderMarkdown(markdown, citations) {
  elements.markdownBody.replaceChildren();
  const citationMap = new Map();
  citations.forEach((item, index) => {
    const entries = citationMap.get(item.marker) || [];
    entries.push({ ...item, number: index + 1 });
    citationMap.set(item.marker, entries);
  });
  const lines = markdown.replaceAll("\r\n", "\n").split("\n");
  let index = 0;

  while (index < lines.length) {
    const line = lines[index];
    if (!line.trim()) {
      index += 1;
      continue;
    }
    if (line.startsWith("```")) {
      const code = [];
      index += 1;
      while (index < lines.length && !lines[index].startsWith("```")) {
        code.push(lines[index]);
        index += 1;
      }
      index += 1;
      const pre = document.createElement("pre");
      const codeElement = document.createElement("code");
      codeElement.textContent = code.join("\n");
      pre.append(codeElement);
      elements.markdownBody.append(pre);
      continue;
    }
    const heading = line.match(/^(#{1,3})\s+(.+)$/);
    if (heading) {
      const node = document.createElement(`h${heading[1].length}`);
      appendInline(node, heading[2], citationMap);
      elements.markdownBody.append(node);
      index += 1;
      continue;
    }
    if (/^[-*]\s+/.test(line)) {
      const list = document.createElement("ul");
      while (index < lines.length && /^[-*]\s+/.test(lines[index])) {
        const item = document.createElement("li");
        appendInline(item, lines[index].replace(/^[-*]\s+/, ""), citationMap);
        list.append(item);
        index += 1;
      }
      elements.markdownBody.append(list);
      continue;
    }
    if (/^\d+\.\s+/.test(line)) {
      const list = document.createElement("ol");
      while (index < lines.length && /^\d+\.\s+/.test(lines[index])) {
        const item = document.createElement("li");
        appendInline(item, lines[index].replace(/^\d+\.\s+/, ""), citationMap);
        list.append(item);
        index += 1;
      }
      elements.markdownBody.append(list);
      continue;
    }
    if (line.startsWith("> ")) {
      const quote = document.createElement("blockquote");
      const quoteLines = [];
      while (index < lines.length && lines[index].startsWith("> ")) {
        quoteLines.push(lines[index].slice(2));
        index += 1;
      }
      appendInline(quote, quoteLines.join(" "), citationMap);
      elements.markdownBody.append(quote);
      continue;
    }

    const paragraphLines = [line.trim()];
    index += 1;
    while (index < lines.length && lines[index].trim() && !isBlockStart(lines[index])) {
      paragraphLines.push(lines[index].trim());
      index += 1;
    }
    const paragraph = document.createElement("p");
    appendInline(paragraph, paragraphLines.join(" "), citationMap);
    elements.markdownBody.append(paragraph);
  }
}

function isBlockStart(line) {
  return /^(#{1,3})\s+/.test(line) || line.startsWith("```") || /^[-*]\s+/.test(line) || /^\d+\.\s+/.test(line) || line.startsWith("> ");
}

function appendInline(parent, text, citationMap) {
  const citationPattern = /\^\[[^\]]+\]/g;
  let cursor = 0;
  for (const match of text.matchAll(citationPattern)) {
    parent.append(document.createTextNode(text.slice(cursor, match.index)));
    const citations = citationMap.get(match[0]) || [];
    if (citations.length) {
      citations.forEach((citation) => {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "citation-button";
        button.textContent = citation.number;
        button.title = `${citation.path}:${citation.start}-${citation.end}`;
        button.setAttribute("aria-label", `Open citation ${citation.number}: ${citation.path}, lines ${citation.start} to ${citation.end}`);
        button.addEventListener("click", () => openCitation(citation, button));
        parent.append(button);
      });
    } else {
      parent.append(document.createTextNode(match[0]));
    }
    cursor = match.index + match[0].length;
  }
  parent.append(document.createTextNode(text.slice(cursor)));
}

async function openCitation(citation, button) {
  document.querySelectorAll(".citation-button").forEach((item) => item.classList.remove("active"));
  button.classList.add("active");
  const params = new URLSearchParams({
    path: citation.path,
    start: citation.start,
    end: citation.end,
  });
  const data = await fetchJson(`/api/source?${params.toString()}`);
  elements.evidenceEmpty.classList.add("hidden");
  elements.evidenceContent.classList.remove("hidden");
  elements.evidenceTitle.textContent = data.title;
  elements.evidenceRange.textContent = `Lines ${data.start}–${data.end}`;
  elements.evidencePath.textContent = data.path;
  elements.sourceLines.replaceChildren();
  elements.sourceLines.start = data.start;
  data.lines.forEach((line) => {
    const item = document.createElement("li");
    item.value = line.number;
    item.textContent = line.text || " ";
    elements.sourceLines.append(item);
  });
}

function resetEvidence() {
  elements.evidenceTitle.textContent = "Source lines";
  elements.evidenceRange.textContent = "";
  elements.evidencePath.textContent = "";
  elements.sourceLines.replaceChildren();
  elements.evidenceContent.classList.add("hidden");
  elements.evidenceEmpty.classList.remove("hidden");
}

async function switchPrimaryView(view) {
  document.querySelectorAll(".tab-button").forEach((button) => {
    button.classList.toggle("active", button.dataset.view === view);
  });
  elements.libraryView.classList.toggle("hidden", view !== "library");
  elements.graphView.classList.toggle("hidden", view !== "graph");
  if (view === "graph") {
    if (!state.graphLoaded) {
      await loadGraph();
    } else {
      state.graph.resize();
      if (elements.graphSearch.value.trim()) {
        searchGraph();
      } else {
        state.graph.fit(undefined, 36);
      }
    }
  }
}

async function loadGraph() {
  const data = await fetchJson("/api/graph");
  elements.graphConceptCount.textContent = data.counts.concepts;
  elements.graphSourceCount.textContent = data.counts.sources;
  elements.graphEdgeCount.textContent = data.counts.edges;
  const graphElements = [
    ...data.nodes.map((node) => ({ data: node })),
    ...data.edges.map((edge) => ({ data: edge })),
  ];

  state.graph = cytoscape({
    container: elements.graphCanvas,
    elements: graphElements,
    minZoom: 0.15,
    maxZoom: 2.5,
    style: [
      {
        selector: "node",
        style: {
          label: "data(label)",
          "font-family": "Inter, system-ui, sans-serif",
          "font-size": 8,
          color: "#26312b",
          "text-wrap": "ellipsis",
          "text-max-width": 92,
          "text-valign": "bottom",
          "text-margin-y": 7,
          "border-width": 2,
          "border-color": "#ffffff",
          "overlay-opacity": 0,
        },
      },
      {
        selector: 'node[type = "concept"]',
        style: {
          shape: "ellipse",
          width: "mapData(source_count, 1, 5, 18, 38)",
          height: "mapData(source_count, 1, 5, 18, 38)",
          "background-color": "#116b57",
        },
      },
      {
        selector: 'node[type = "source"]',
        style: {
          shape: "round-rectangle",
          width: 16,
          height: 16,
          "background-color": "#53616b",
          label: "",
        },
      },
      {
        selector: 'node[status = "pending_review"]',
        style: {
          "border-style": "dashed",
          "border-color": "#8eb5a8",
        },
      },
      {
        selector: "edge",
        style: {
          width: "mapData(confidence, 0.5, 1, 0.6, 1.8)",
          "line-color": "#b9c0ba",
          "curve-style": "haystack",
          opacity: 0.65,
          "overlay-opacity": 0,
        },
      },
      {
        selector: ".faded",
        style: { opacity: 0.08, "text-opacity": 0 },
      },
      {
        selector: ".matched",
        style: {
          "border-width": 4,
          "border-color": "#1677ff",
          "text-opacity": 1,
          opacity: 1,
          "z-index": 20,
        },
      },
      {
        selector: ":selected",
        style: {
          "border-width": 4,
          "border-color": "#d49a36",
          "line-color": "#d49a36",
          "z-index": 30,
        },
      },
    ],
    layout: {
      name: "cose",
      animate: false,
      fit: true,
      padding: 36,
      nodeRepulsion: 9000,
      idealEdgeLength: 70,
      gravity: 0.35,
      numIter: 800,
    },
  });

  state.graph.on("tap", "node", (event) => selectGraphNode(event.target));
  state.graph.on("tap", (event) => {
    if (event.target === state.graph) {
      resetGraphView();
    }
  });
  elements.graphLoading.classList.add("hidden");
  state.graphLoaded = true;
}

function selectGraphNode(node) {
  const neighborhood = node.closedNeighborhood();
  state.graph.elements().addClass("faded");
  neighborhood.removeClass("faded");
  node.select();
  state.graph.animate({ fit: { eles: neighborhood, padding: 80 }, duration: 220 });

  const data = node.data();
  elements.graphSelection.replaceChildren();
  const eyebrow = document.createElement("span");
  eyebrow.className = "panel-eyebrow";
  eyebrow.textContent = data.type;
  const title = document.createElement("strong");
  title.textContent = data.label;
  const meta = document.createElement("span");
  meta.className = "selection-meta";
  if (data.type === "concept") {
    meta.textContent = `${data.source_count} source${data.source_count === 1 ? "" : "s"} · ${String(data.status).replaceAll("_", " ")}`;
  } else {
    meta.textContent = `${node.connectedEdges().length} concept${node.connectedEdges().length === 1 ? "" : "s"}`;
  }
  const description = document.createElement("p");
  description.textContent = data.summary || data.path || "No description";
  elements.graphSelection.append(eyebrow, title, meta, description);

  if (data.type === "concept" && data.document_kind && data.document_id) {
    const openButton = document.createElement("button");
    openButton.type = "button";
    openButton.className = "secondary-button";
    openButton.textContent = data.document_kind === "draft"
      ? "Open draft"
      : `Open ${data.document_kind} page`;
    openButton.addEventListener("click", async () => {
      await switchPrimaryView("library");
      elements.documentSearch.value = "";
      await switchDocumentKind(data.document_kind, data.document_id);
    });
    elements.graphSelection.append(openButton);
  }
}

function searchGraph() {
  if (!state.graph) {
    return;
  }
  const query = elements.graphSearch.value.trim().toLocaleLowerCase();
  state.graph.nodes().removeClass("matched faded");
  if (!query) {
    state.graph.edges().removeClass("faded");
    return;
  }
  const matches = state.graph.nodes().filter((node) => {
    const data = node.data();
    return [data.label, data.summary, data.path, ...(data.tags || [])]
      .join(" ")
      .toLocaleLowerCase()
      .includes(query);
  });
  state.graph.elements().addClass("faded");
  matches.addClass("matched").removeClass("faded");
  matches.connectedEdges().removeClass("faded");
  if (matches.length) {
    state.graph.animate({ fit: { eles: matches, padding: 100 }, duration: 180 });
  }
}

function resetGraphView() {
  if (!state.graph) {
    return;
  }
  elements.graphSearch.value = "";
  state.graph.elements().removeClass("faded matched").unselect();
  state.graph.animate({ fit: { eles: state.graph.elements(), padding: 36 }, duration: 220 });
  elements.graphSelection.innerHTML = "<span class=\"panel-eyebrow\">Selection</span><strong>Explore the graph</strong><p>Select a concept or source to isolate its evidence neighborhood.</p>";
}

async function fetchJson(url) {
  const response = await fetch(url, { headers: { Accept: "application/json" } });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || `Request failed: ${response.status}`);
  }
  return payload;
}

async function postJson(url, body) {
  const response = await fetch(url, {
    method: "POST",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || `Request failed: ${response.status}`);
  }
  return payload;
}

function showFatalError(error) {
  elements.readerContent.classList.add("hidden");
  elements.readerEmpty.classList.remove("hidden");
  elements.readerEmpty.querySelector("strong").textContent = "Viewer failed to load";
  elements.readerEmpty.querySelector("p").textContent = error instanceof Error ? error.message : String(error);
}
