/**
 * Builds doc/presentation/document_search_platform.pptx
 *
 * Run: node doc/presentation/build_deck.js
 * (requires pptxgenjs; the rendered architecture diagrams in
 * doc/architecture/*.png must exist -- run `mmdc` on the .mmd sources first
 * if regenerating from scratch.)
 */
const pptxgen = require("pptxgenjs");
const path = require("path");

const ARCH_DIR = path.join(__dirname, "..", "architecture");
const OUT = path.join(__dirname, "document_search_platform.pptx");

// Midnight Executive palette
const NAVY = "1E2761";
const NAVY_DARK = "141B4D";
const ICE = "CADCFC";
const WHITE = "FFFFFF";
const INK = "1F2430";
const MUTED = "6B7280";
const ACCENT = "3D8BFD";
const CARD_BG = "F4F7FE";

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.33 x 7.5 in
const PAGE_W = 13.33;
const MARGIN = 0.6;

function titleSlide() {
  const s = pres.addSlide();
  s.background = { color: NAVY };
  s.addShape(pres.ShapeType.ellipse, {
    x: 9.8, y: -2.2, w: 6, h: 6, fill: { color: NAVY_DARK }, line: { type: "none" },
  });
  s.addShape(pres.ShapeType.ellipse, {
    x: -2.5, y: 4.8, w: 5, h: 5, fill: { color: NAVY_DARK }, line: { type: "none" },
  });
  s.addText("DOCUMENT SEARCH PLATFORM", {
    x: MARGIN, y: 2.55, w: 10.5, h: 0.5, fontFace: "Calibri", fontSize: 15,
    color: ICE, charSpacing: 3, bold: true, margin: 0,
  });
  s.addText("An Agentic, Contextual RAG Backend", {
    x: MARGIN, y: 3.0, w: 11.5, h: 1.1, fontFace: "Cambria", fontSize: 40,
    color: WHITE, bold: true, margin: 0,
  });
  s.addText("Docling  •  PostgreSQL + PGVector  •  LlamaIndex  •  CrewAI  •  Ollama  •  Arize Phoenix  •  RAGAs  •  OpenWebUI", {
    x: MARGIN, y: 4.05, w: 11.8, h: 0.5, fontFace: "Calibri", fontSize: 13.5,
    color: ICE, italic: true, margin: 0,
  });
  s.addText("Technical Assessment — Solution Overview", {
    x: MARGIN, y: 6.55, w: 8, h: 0.4, fontFace: "Calibri", fontSize: 12, color: "8FA3D9", margin: 0,
  });
}

function sectionHeader(s, kicker, title) {
  s.background = { color: WHITE };
  s.addText(kicker.toUpperCase(), {
    x: MARGIN, y: 0.45, w: 10, h: 0.35, fontFace: "Calibri", fontSize: 12,
    color: ACCENT, bold: true, charSpacing: 2, margin: 0,
  });
  s.addText(title, {
    x: MARGIN, y: 0.78, w: 12, h: 0.7, fontFace: "Cambria", fontSize: 28,
    color: NAVY, bold: true, margin: 0,
  });
}

function pageNum(s, n) {
  s.addText(String(n).padStart(2, "0"), {
    x: PAGE_W - 0.9, y: 7.05, w: 0.6, h: 0.3, fontFace: "Calibri", fontSize: 10,
    color: MUTED, align: "right", margin: 0,
  });
}

// ---------------------------------------------------------------------- //
// Slide 2: What we built
// ---------------------------------------------------------------------- //
function whatWeBuilt() {
  const s = pres.addSlide();
  sectionHeader(s, "Overview", "What We Built");

  const items = [
    { t: "Agentic RAG Backend", d: "A FastAPI service where a CrewAI agent crew plans, retrieves, synthesizes, and verifies every answer before it's returned." },
    { t: "REST API, Fully Documented", d: "OpenAPI/Swagger-described endpoints for ingestion, retrieval, chat, prompts, and evaluation." },
    { t: "OpenWebUI Frontend", d: "Connected via an OpenAI-compatible /v1/chat/completions surface — no custom plugin runtime required." },
    { t: "Traced & Evaluated", d: "Every inference call traced in Arize Phoenix; pipeline quality measured with RAGAs against a curated Q&A set." },
  ];

  const colW = 5.85, gapX = 0.35, rowY = 1.85, cardH = 2.15, gapY = 0.35;
  items.forEach((it, i) => {
    const col = i % 2, row = Math.floor(i / 2);
    const x = MARGIN + col * (colW + gapX);
    const y = rowY + row * (cardH + gapY);
    s.addShape(pres.ShapeType.roundRect, {
      x, y, w: colW, h: cardH, rectRadius: 0.08,
      fill: { color: CARD_BG }, line: { type: "none" },
      shadow: { type: "outer", color: "1E2761", opacity: 0.12, blur: 6, offset: 2, angle: 90 },
    });
    s.addShape(pres.ShapeType.ellipse, {
      x: x + 0.3, y: y + 0.3, w: 0.5, h: 0.5, fill: { color: NAVY }, line: { type: "none" },
    });
    s.addText(String(i + 1), {
      x: x + 0.3, y: y + 0.3, w: 0.5, h: 0.5, fontFace: "Calibri", fontSize: 16,
      color: WHITE, bold: true, align: "center", valign: "middle", margin: 0,
    });
    s.addText(it.t, {
      x: x + 0.95, y: y + 0.28, w: colW - 1.2, h: 0.5, fontFace: "Calibri", fontSize: 16,
      color: NAVY, bold: true, margin: 0,
    });
    s.addText(it.d, {
      x: x + 0.3, y: y + 0.95, w: colW - 0.6, h: cardH - 1.15, fontFace: "Calibri", fontSize: 12.5,
      color: INK, margin: 0, valign: "top",
    });
  });
  pageNum(s, 2);
}

// ---------------------------------------------------------------------- //
// Slide 3: Mandated toolset -> role
// ---------------------------------------------------------------------- //
function toolsetSlide() {
  const s = pres.addSlide();
  sectionHeader(s, "Requirements Traceability", "Mandated Toolset → Role in This Build");

  const rows = [
    ["Docling", "PDF/DOCX preprocessing: layout, table structure, Markdown export"],
    ["PostgreSQL + PGVector", "Sole vector store — HNSW / cosine index over document_chunks"],
    ["LlamaIndex", "Node parsing, embedding, and retrieval orchestration"],
    ["CrewAI", "4-agent contextual RAG crew with a verify → retry loop"],
    ["Ollama", "Sole LLM + embedding provider — generation, agents, and RAGAs judge"],
    ["Arize Phoenix", "OpenInference tracing for every LLM / agent / tool call"],
    ["RAGAs", "Faithfulness, answer relevancy, context precision & recall"],
    ["OpenWebUI", "Chat frontend via the OpenAI-compatible API surface"],
  ];

  const startY = 1.75, rowH = 0.585;
  s.addShape(pres.ShapeType.roundRect, {
    x: MARGIN, y: startY, w: 12.13, h: rowH, rectRadius: 0.06,
    fill: { color: NAVY }, line: { type: "none" },
  });
  s.addText("Tool", { x: MARGIN + 0.25, y: startY, w: 3.3, h: rowH, fontFace: "Calibri", fontSize: 13, bold: true, color: WHITE, valign: "middle", margin: 0 });
  s.addText("Role in this build", { x: MARGIN + 3.6, y: startY, w: 8, h: rowH, fontFace: "Calibri", fontSize: 13, bold: true, color: WHITE, valign: "middle", margin: 0 });

  rows.forEach((r, i) => {
    const y = startY + rowH * (i + 1);
    if (i % 2 === 0) {
      s.addShape(pres.ShapeType.rect, { x: MARGIN, y, w: 12.13, h: rowH, fill: { color: CARD_BG }, line: { type: "none" } });
    }
    s.addText(r[0], { x: MARGIN + 0.25, y, w: 3.3, h: rowH, fontFace: "Calibri", fontSize: 12.5, bold: true, color: NAVY, valign: "middle", margin: 0 });
    s.addText(r[1], { x: MARGIN + 3.6, y, w: 8.3, h: rowH, fontFace: "Calibri", fontSize: 12, color: INK, valign: "middle", margin: 0 });
  });
  pageNum(s, 3);
}

// ---------------------------------------------------------------------- //
// Slide: full-bleed diagram slide
// ---------------------------------------------------------------------- //
function diagramSlide(kicker, title, imgPath, caption, num, imgOpts) {
  const s = pres.addSlide();
  sectionHeader(s, kicker, title);
  const opts = Object.assign({ x: 0.9, y: 1.7, w: 11.5, h: 5.1, sizing: { type: "contain", w: 11.5, h: 5.1 } }, imgOpts || {});
  s.addImage({ path: imgPath, ...opts });
  if (caption) {
    s.addText(caption, {
      x: MARGIN, y: 6.95, w: 12, h: 0.35, fontFace: "Calibri", fontSize: 10.5,
      color: MUTED, italic: true, margin: 0,
    });
  }
  pageNum(s, num);
}

// ---------------------------------------------------------------------- //
// Slide: Agentic crew (2x2 agent cards + loop note)
// ---------------------------------------------------------------------- //
function crewSlide() {
  const s = pres.addSlide();
  sectionHeader(s, "Core Design", "The Agentic RAG Crew");

  const agents = [
    { t: "1. Query Analyzer", d: "Rewrites the question, resolves chat-history context, plans 1–3 focused sub-queries." },
    { t: "2. Retriever", d: "Calls the search_knowledge_base tool (LlamaIndex + PGVector) per sub-query; flags evidence gaps explicitly." },
    { t: "3. Synthesizer", d: "Writes a direct, cited answer using only the retrieved evidence — no fabrication from general knowledge." },
    { t: "4. Verifier", d: "Checks every claim against the evidence. APPROVE, or REJECT with a refined query for another pass." },
  ];
  const colW = 5.85, gapX = 0.35, rowY = 1.75, cardH = 1.95, gapY = 0.3;
  agents.forEach((a, i) => {
    const col = i % 2, row = Math.floor(i / 2);
    const x = MARGIN + col * (colW + gapX);
    const y = rowY + row * (cardH + gapY);
    s.addShape(pres.ShapeType.roundRect, {
      x, y, w: colW, h: cardH, rectRadius: 0.08,
      fill: { color: i === 3 ? NAVY : CARD_BG }, line: { type: "none" },
      shadow: { type: "outer", color: "1E2761", opacity: 0.12, blur: 6, offset: 2, angle: 90 },
    });
    s.addText(a.t, {
      x: x + 0.3, y: y + 0.22, w: colW - 0.6, h: 0.45, fontFace: "Calibri", fontSize: 15.5,
      bold: true, color: i === 3 ? WHITE : NAVY, margin: 0,
    });
    s.addText(a.d, {
      x: x + 0.3, y: y + 0.72, w: colW - 0.6, h: cardH - 0.9, fontFace: "Calibri", fontSize: 12,
      color: i === 3 ? ICE : INK, margin: 0, valign: "top",
    });
  });

  s.addText("The Retriever → Synthesizer → Verifier hand-off runs as a CrewAI sequential crew; a REJECT verdict feeds the refined query back into the Retriever for up to CREW_MAX_ITERATIONS passes — this loop is what makes the pipeline agentic and contextual rather than a single retrieve-then-generate call.", {
    x: MARGIN, y: 6.55, w: 12.1, h: 0.7, fontFace: "Calibri", fontSize: 11.5,
    color: MUTED, italic: true, margin: 0,
  });
  pageNum(s, 6);
}

// ---------------------------------------------------------------------- //
// Slide: Prompt externalization
// ---------------------------------------------------------------------- //
function promptsSlide() {
  const s = pres.addSlide();
  sectionHeader(s, "PromptOps", "Prompts Externalized From Application Code");

  s.addShape(pres.ShapeType.roundRect, {
    x: MARGIN, y: 1.75, w: 6.4, h: 4.85, rectRadius: 0.08,
    fill: { color: NAVY_DARK }, line: { type: "none" },
  });
  const code = [
    "name: verifier_agent",
    "version: \"1.0.0\"",
    "role: >",
    "  Faithfulness & Groundedness Reviewer",
    "goal: >",
    "  Approve the answer, or reject it with",
    "  a refined search query.",
    "description: |",
    "  Draft answer: $draft_answer",
    "  Evidence: $evidence",
    "  Check every claim, then decide:",
    "  APPROVE or REJECT + refined_query.",
  ];
  s.addText(
    code.map((l, i) => ({ text: l, options: { breakLine: true, color: i < 2 ? "8FA3D9" : (l.endsWith(":") || l.endsWith(": >") || l.endsWith(": |") ? "6FD3A0" : WHITE) } })),
    { x: MARGIN + 0.3, y: 1.98, w: 5.8, h: 4.4, fontFace: "Consolas", fontSize: 12.5, valign: "top", margin: 0, lineSpacingMultiple: 1.25 }
  );

  const bullets = [
    "Every agent persona + task prompt lives in app/prompts/library/*.yaml — zero hardcoded prompt strings in Python.",
    "Semantically versioned per file, so a Phoenix trace can record exactly which prompt version produced a given span.",
    "Hot-reloadable via POST /api/v1/prompts/reload — a wording change ships without a redeploy.",
    "GET /api/v1/prompts exposes the live inventory for audit.",
  ];
  let by = 1.85;
  bullets.forEach((b) => {
    s.addShape(pres.ShapeType.ellipse, { x: 7.15, y: by + 0.09, w: 0.12, h: 0.12, fill: { color: ACCENT }, line: { type: "none" } });
    const h = 0.95;
    s.addText(b, { x: 7.4, y: by - 0.08, w: 5.3, h, fontFace: "Calibri", fontSize: 13, color: INK, margin: 0, valign: "top" });
    by += h + 0.15;
  });
  pageNum(s, 8);
}

// ---------------------------------------------------------------------- //
// Slide: Observability
// ---------------------------------------------------------------------- //
function observabilitySlide() {
  const s = pres.addSlide();
  sectionHeader(s, "Observability", "Every Inference Call Is Traced");

  const stats = [
    { n: "3", l: "libraries instrumented\n(LlamaIndex, CrewAI, LiteLLM)" },
    { n: "1x", l: "instrumentation point\n(FastAPI startup event)" },
    { n: "100%", l: "of LLM / agent / tool calls\ncovered by construction" },
  ];
  const cw = 3.75, gap = 0.3;
  stats.forEach((st, i) => {
    const x = MARGIN + i * (cw + gap);
    s.addShape(pres.ShapeType.roundRect, {
      x, y: 1.8, w: cw, h: 1.8, rectRadius: 0.08, fill: { color: NAVY }, line: { type: "none" },
    });
    s.addText(st.n, { x, y: 1.95, w: cw, h: 0.85, fontFace: "Cambria", fontSize: 38, bold: true, color: WHITE, align: "center", margin: 0 });
    s.addText(st.l, { x: x + 0.2, y: 2.75, w: cw - 0.4, h: 0.75, fontFace: "Calibri", fontSize: 11.5, color: ICE, align: "center", margin: 0 });
  });

  const bullets = [
    "init_tracing() runs once, before the first request — a new call site added later is traced automatically, not opt-in.",
    "Phoenix captures the full query-analysis → retrieve → synthesize → verify span tree, including every retry iteration.",
    "Each span records prompt, completion, latency, and token usage — plus the exact search_knowledge_base tool arguments and results.",
    "Phoenix UI doubles as a debugging tool: a low-faithfulness eval score points straight at the offending span.",
  ];
  let by = 4.0;
  bullets.forEach((b) => {
    s.addShape(pres.ShapeType.ellipse, { x: MARGIN + 0.02, y: by + 0.09, w: 0.12, h: 0.12, fill: { color: ACCENT }, line: { type: "none" } });
    s.addText(b, { x: MARGIN + 0.3, y: by - 0.06, w: 11.6, h: 0.6, fontFace: "Calibri", fontSize: 13, color: INK, margin: 0, valign: "top" });
    by += 0.68;
  });
  pageNum(s, 9);
}

// ---------------------------------------------------------------------- //
// Slide: Evaluation
// ---------------------------------------------------------------------- //
function evalSlide() {
  const s = pres.addSlide();
  sectionHeader(s, "Quality", "Evaluation With RAGAs");

  const metrics = [
    { t: "Faithfulness", d: "Is the answer supported by the retrieved context?" },
    { t: "Answer Relevancy", d: "Does the answer address the actual question?" },
    { t: "Context Precision", d: "How much of what was retrieved is relevant?" },
    { t: "Context Recall", d: "Did retrieval surface what the reference answer needs?" },
  ];
  const cw = 2.85, gap = 0.25;
  metrics.forEach((m, i) => {
    const x = MARGIN + i * (cw + gap);
    s.addShape(pres.ShapeType.roundRect, {
      x, y: 1.8, w: cw, h: 2.1, rectRadius: 0.08, fill: { color: CARD_BG }, line: { type: "none" },
      shadow: { type: "outer", color: "1E2761", opacity: 0.12, blur: 6, offset: 2, angle: 90 },
    });
    s.addText(m.t, { x: x + 0.2, y: 1.98, w: cw - 0.4, h: 0.65, fontFace: "Calibri", fontSize: 14, bold: true, color: NAVY, margin: 0 });
    s.addText(m.d, { x: x + 0.2, y: 2.6, w: cw - 0.4, h: 1.2, fontFace: "Calibri", fontSize: 11.5, color: INK, margin: 0, valign: "top" });
  });

  const bullets = [
    "Judged by the same Ollama-backed LlamaIndex LLM/embeddings used in production — no OpenAI key anywhere in the stack.",
    "Runs every curated question through the real run_agentic_rag() path (not a retrieval-only shortcut), so scores reflect what a user actually experiences, retries included.",
    "12-question seed set over the placeholder corpus; app/prompts/library/ragas_testset_seed.yaml bootstraps more questions once the real corpus is ingested.",
  ];
  let by = 4.25;
  bullets.forEach((b) => {
    s.addShape(pres.ShapeType.ellipse, { x: MARGIN + 0.02, y: by + 0.09, w: 0.12, h: 0.12, fill: { color: ACCENT }, line: { type: "none" } });
    s.addText(b, { x: MARGIN + 0.3, y: by - 0.06, w: 11.6, h: 0.65, fontFace: "Calibri", fontSize: 13, color: INK, margin: 0, valign: "top" });
    by += 0.72;
  });
  s.addText("Full methodology + latest results: doc/evaluation/evaluation_report.md", {
    x: MARGIN, y: 6.85, w: 11, h: 0.35, fontFace: "Calibri", fontSize: 10.5, color: MUTED, italic: true, margin: 0,
  });
  pageNum(s, 10);
}

// ---------------------------------------------------------------------- //
// Slide: Deployment & API
// ---------------------------------------------------------------------- //
function deploymentSlide() {
  const s = pres.addSlide();
  sectionHeader(s, "Deployment", "One Compose File, Five Services");

  const services = [
    "postgres  — pgvector/pgvector:pg16",
    "ollama  — LLM + embedding models",
    "phoenix  — trace collector + UI",
    "backend  — this FastAPI app",
    "openwebui  — chat frontend",
  ];
  s.addShape(pres.ShapeType.roundRect, {
    x: MARGIN, y: 1.75, w: 5.5, h: 4.85, rectRadius: 0.08, fill: { color: NAVY }, line: { type: "none" },
  });
  s.addText("docker compose up -d --build", {
    x: MARGIN + 0.3, y: 1.98, w: 5, h: 0.4, fontFace: "Consolas", fontSize: 12.5, color: "6FD3A0", margin: 0,
  });
  services.forEach((svc, i) => {
    s.addText(svc, {
      x: MARGIN + 0.3, y: 2.55 + i * 0.6, w: 4.9, h: 0.5, fontFace: "Consolas", fontSize: 12.5,
      color: WHITE, margin: 0, valign: "middle",
    });
  });
  s.addText("+ ollama-pull (one-shot model download)", {
    x: MARGIN + 0.3, y: 5.75, w: 4.9, h: 0.4, fontFace: "Calibri", fontSize: 11, italic: true, color: ICE, margin: 0,
  });

  const endpoints = [
    ["POST", "/api/v1/ingest", "Docling → split → embed → index"],
    ["POST", "/api/v1/query", "Rich RAG answer + sources + trace"],
    ["POST", "/api/v1/search", "Raw retrieval, no generation"],
    ["GET/POST", "/api/v1/prompts", "Inspect / hot-reload prompts"],
    ["POST", "/api/v1/eval/run", "Run the RAGAs harness"],
    ["POST", "/v1/chat/completions", "OpenAI-compatible — OpenWebUI"],
  ];
  const ex = 6.35, ew = 6.4, rh = 0.63;
  s.addText("REST API  (full spec: doc/api/openapi.json)", {
    x: ex, y: 1.75, w: ew, h: 0.35, fontFace: "Calibri", fontSize: 12.5, bold: true, color: NAVY, margin: 0,
  });
  endpoints.forEach((e, i) => {
    const y = 2.25 + i * rh;
    if (i % 2 === 0) s.addShape(pres.ShapeType.rect, { x: ex, y, w: ew, h: rh, fill: { color: CARD_BG }, line: { type: "none" } });
    s.addText(e[0], { x: ex + 0.15, y, w: 0.9, h: rh, fontFace: "Consolas", fontSize: 10.5, bold: true, color: ACCENT, valign: "middle", margin: 0 });
    s.addText(e[1], { x: ex + 1.05, y, w: 2.55, h: rh, fontFace: "Consolas", fontSize: 10.5, color: NAVY, valign: "middle", margin: 0 });
    s.addText(e[2], { x: ex + 3.6, y, w: ew - 3.7, h: rh, fontFace: "Calibri", fontSize: 10.5, color: INK, valign: "middle", margin: 0 });
  });
  pageNum(s, 11);
}

// ---------------------------------------------------------------------- //
// Slide: Limitations & roadmap
// ---------------------------------------------------------------------- //
function roadmapSlide() {
  const s = pres.addSlide();
  sectionHeader(s, "Status", "Delivered, and What's Next");

  s.addText("DELIVERED", { x: MARGIN, y: 1.7, w: 5.8, h: 0.35, fontFace: "Calibri", fontSize: 13, bold: true, color: ACCENT, charSpacing: 1, margin: 0 });
  const delivered = [
    "Full source: ingestion, agentic crew, API, tracing, eval",
    "docker-compose stack for all 5 services",
    "Architecture diagrams + ADR-style design doc",
    "Swagger/OpenAPI spec + Postman-ready REST surface",
    "Externalized, versioned, hot-reloadable prompts",
  ];
  let dy = 2.15;
  delivered.forEach((d) => {
    s.addShape(pres.ShapeType.ellipse, { x: MARGIN + 0.02, y: dy + 0.09, w: 0.12, h: 0.12, fill: { color: "2FA86B" }, line: { type: "none" } });
    s.addText(d, { x: MARGIN + 0.3, y: dy - 0.08, w: 5.5, h: 0.6, fontFace: "Calibri", fontSize: 12.5, color: INK, margin: 0, valign: "top" });
    dy += 0.68;
  });

  const nx = 6.9;
  s.addText("NEXT STEPS", { x: nx, y: 1.7, w: 5.8, h: 0.35, fontFace: "Calibri", fontSize: 13, bold: true, color: "C2410C", charSpacing: 1, margin: 0 });
  const next = [
    "Swap sample_docs/ placeholders for the real Google Drive corpus",
    "Run the live stack end-to-end and record real Phoenix traces + RAGAs scores",
    "Streaming responses; native OpenWebUI citation cards via a Pipelines plugin",
    "Content-hash based incremental ingestion for large, changing corpora",
    "Per-user auth / document ACLs for multi-tenant deployment",
  ];
  let ny = 2.15;
  next.forEach((d) => {
    s.addShape(pres.ShapeType.ellipse, { x: nx + 0.02, y: ny + 0.09, w: 0.12, h: 0.12, fill: { color: "C2410C" }, line: { type: "none" } });
    s.addText(d, { x: nx + 0.3, y: ny - 0.08, w: 5.9, h: 0.6, fontFace: "Calibri", fontSize: 12.5, color: INK, margin: 0, valign: "top" });
    ny += 0.68;
  });
  pageNum(s, 12);
}

function closingSlide() {
  const s = pres.addSlide();
  s.background = { color: NAVY };
  s.addShape(pres.ShapeType.ellipse, { x: 9.8, y: -2.2, w: 6, h: 6, fill: { color: NAVY_DARK }, line: { type: "none" } });
  s.addText("Thank You", { x: MARGIN, y: 2.9, w: 10, h: 1.1, fontFace: "Cambria", fontSize: 42, bold: true, color: WHITE, margin: 0 });
  s.addText("Full source, docs, and diagrams: this repository's README.md", {
    x: MARGIN, y: 3.95, w: 10.5, h: 0.5, fontFace: "Calibri", fontSize: 14, color: ICE, margin: 0,
  });
  s.addText("doc/architecture/architecture.md  •  doc/api/openapi.json  •  doc/evaluation/evaluation_report.md", {
    x: MARGIN, y: 4.45, w: 11, h: 0.4, fontFace: "Calibri", fontSize: 11.5, color: "8FA3D9", italic: true, margin: 0,
  });
}

titleSlide();
whatWeBuilt();
toolsetSlide();
diagramSlide("Architecture", "System Architecture", path.join(ARCH_DIR, "system_architecture.png"),
  "Component view: client layer, agentic RAG backend, data layer, LLM layer, and observability — see doc/architecture/architecture.md for the full rationale.", 4);
diagramSlide("Ingestion", "Docling → Split → Embed → Index", path.join(ARCH_DIR, "ingestion_flow.png"),
  "Heading-aware splitting first (MarkdownNodeParser), then a token-size ceiling (SentenceSplitter) — chunks never straddle unrelated sections.", 5,
  { x: 1.6, y: 2.6, w: 10.1, h: 3.4, sizing: { type: "contain", w: 10.1, h: 3.4 } });
crewSlide();
diagramSlide("Request Flow", "Agentic RAG — Sequence", path.join(ARCH_DIR, "agentic_rag_sequence.png"),
  "Verifier rejections feed a refined query back into the Retriever — up to CREW_MAX_ITERATIONS passes — before the API returns a final, cited answer.", 7,
  { x: 1.1, y: 1.6, w: 11.1, h: 5.3, sizing: { type: "contain", w: 11.1, h: 5.3 } });
promptsSlide();
observabilitySlide();
evalSlide();
deploymentSlide();
roadmapSlide();
closingSlide();

pres.writeFile({ fileName: OUT }).then(() => console.log("wrote", OUT));
