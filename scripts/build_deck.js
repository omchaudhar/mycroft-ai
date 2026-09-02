// Business proposal deck for Mycroft.ai.
// Content mirrors docs/BUSINESS_PROPOSAL.md; every figure comes from outputs/.
const pptx = new (require("pptxgenjs"))();
const OUT = process.argv[2] || "Mycroft_AI_Business_Proposal.pptx";

pptx.layout = "LAYOUT_WIDE";              // 13.3 x 7.5
const W = 13.3, H = 7.5, M = 0.62;
const CW = W - 2 * M;

// Midnight executive: navy dominates, ice blue supports, amber marks cost.
const INK = "0E1330", NAVY = "1E2761", MID = "2E3D7A", ICE = "CADCFC",
      PALE = "F2F5FC", SLATE = "5A6684", WHITE = "FFFFFF", AMBER = "C97B1E",
      GREEN = "1F7A55", LINE = "DDE3F2";

const HEAD = "Cambria", BODY = "Calibri";

pptx.defineSlideMaster({ title: "LIGHT", background: { color: WHITE } });
pptx.defineSlideMaster({ title: "DARK",  background: { color: INK } });

let n = 0;
function slide(dark) {
  const s = pptx.addSlide({ masterName: dark ? "DARK" : "LIGHT" });
  const _addText = s.addText.bind(s);
  s.addText = (t, o) => _addText(t, Object.assign({ valign: "top" }, o));
  n += 1;
  if (!dark && n > 1) {
    s.addText(String(n), { x: W - M - 0.5, y: H - 0.46, w: 0.5, h: 0.26,
      isTextBox: true, margin: 0, align: "right", fontFace: BODY,
      fontSize: 9, color: SLATE });
    s.addText("Mycroft.ai  ·  Business Proposal", { x: M, y: H - 0.46, w: 5, h: 0.26,
      isTextBox: true, margin: 0, fontFace: BODY, fontSize: 9, color: SLATE });
  }
  return s;
}
function title(s, text, kicker) {
  let y = 0.5;
  if (kicker) {
    s.addText(kicker.toUpperCase(), { x: M, y, w: CW, h: 0.26, isTextBox: true,
      margin: 0, fontFace: BODY, fontSize: 11, bold: true, color: MID,
      charSpacing: 1.6 });
    y += 0.34;
  }
  s.addText(text, { x: M, y, w: CW, h: 0.72, isTextBox: true, margin: 0,
    fontFace: HEAD, fontSize: 30, bold: true, color: NAVY });
  return y + 0.92;
}
function card(s, o) {
  s.addShape(pptx.ShapeType.roundRect, {
    x: o.x, y: o.y, w: o.w, h: o.h, rectRadius: 0.07,
    fill: { color: o.fill || PALE }, line: { color: o.line || LINE, width: 0.75 },
    shadow: { type: "outer", color: "8899BB", opacity: 0.18, blur: 6, offset: 1, angle: 90 },
  });
}
function bullets(s, items, o) {
  s.addText(items.map((t, i) => ({
    text: t, options: { bullet: true, breakLine: i < items.length - 1 },
  })), { x: o.x, y: o.y, w: o.w, h: o.h, isTextBox: true, margin: 0,
    fontFace: BODY, fontSize: o.size || 14, color: o.color || INK,
    paraSpaceAfter: 7, lineSpacing: 19 });
}
function stat(s, o) {
  s.addText(o.value, { x: o.x, y: o.y, w: o.w, h: 0.72, isTextBox: true, margin: 0,
    align: o.align || "left", fontFace: HEAD, fontSize: o.size || 40, bold: true,
    color: o.color || NAVY });
  s.addText(o.label, { x: o.x, y: o.y + 0.7, w: o.w, h: 0.52, isTextBox: true,
    margin: 0, align: o.align || "left", fontFace: BODY, fontSize: 11.5,
    color: o.labelColor || SLATE });
}
function table(s, head, rows, o) {
  const body = [
    head.map((h) => ({ text: h, options: {
      bold: true, color: SLATE, fontSize: 10, fontFace: BODY,
      fill: { color: WHITE }, border: [{ pt: 0 }, { pt: 0 }, { pt: 1, color: NAVY }, { pt: 0 }],
    } })),
    ...rows.map((r) => r.map((c, i) => ({
      text: String(c),
      options: { fontSize: o.fs || 11.5, fontFace: BODY, color: INK,
        bold: !!o.boldFirst && i === 0,
        border: [{ pt: 0 }, { pt: 0 }, { pt: 0.5, color: LINE }, { pt: 0 }] },
    }))),
  ];
  s.addTable(body, { x: o.x, y: o.y, w: o.w, colW: o.colW, rowH: o.rowH || 0.36,
    valign: "middle", margin: [4, 7, 4, 7], autoPage: false });
}

/* ───────────────────────────── 1 · title ─────────────────────────── */
{
  const s = slide(true);
  s.addShape(pptx.ShapeType.roundRect, { x: -2, y: -2.4, w: 8.4, h: 8.4,
    rectRadius: 0.5, fill: { color: NAVY, transparency: 62 }, line: { width: 0 } });
  s.addShape(pptx.ShapeType.roundRect, { x: 8.2, y: 3.6, w: 7.6, h: 7.6,
    rectRadius: 0.5, fill: { color: MID, transparency: 72 }, line: { width: 0 } });
  s.addText("Mycroft.ai", { x: M, y: 2.18, w: 10, h: 1.15, isTextBox: true,
    margin: 0, fontFace: HEAD, fontSize: 60, bold: true, color: WHITE });
  s.addText("A configurable Responsible AI control plane for the enterprise AI portfolio",
    { x: M, y: 3.35, w: 10.6, h: 0.6, isTextBox: true, margin: 0,
      fontFace: BODY, fontSize: 19, color: ICE });
  s.addText("BUSINESS PROPOSAL", { x: M, y: 1.72, w: 8, h: 0.3, isTextBox: true,
    margin: 0, fontFace: BODY, fontSize: 12.5, bold: true, color: ICE, charSpacing: 3 });
  s.addText([
    { text: "Team Mycroft.ai", options: { bold: true, color: WHITE } },
    { text: "   ·   IIT Bombay   ·   Accenture Innovation Challenge 2026, Round 2" },
    { text: "\nSubmitted against Track 1: ControlPlane.ai" },
  ], { x: M, y: 5.55, w: 11, h: 0.85, isTextBox: true, margin: 0,
    fontFace: BODY, fontSize: 13, color: "9FB2D8", lineSpacing: 21 });
  s.addNotes("Enterprises don't have an AI system. They have a portfolio of them. That is the whole problem.");
}

/* ───────────────────────── 2 · executive summary ──────────────────── */
{
  const s = slide(false);
  let y = title(s, "One control plane, three commitments", "Executive summary");
  s.addText("Enterprises are not deploying one AI system. They are deploying a portfolio of them, and each carries a different risk signature, latency budget and regulatory obligation. A single checker applied uniformly will be too slow for the first, too noisy for the second, and too shallow for the third.",
    { x: M, y, w: CW, h: 0.78, isTextBox: true, margin: 0, fontFace: BODY,
      fontSize: 14.5, color: INK, lineSpacing: 21 });
  y += 1.02;
  const items = [
    ["01", "Governance is configuration, not code",
     "An Evaluation Contract, merged with a jurisdiction's policy pack, decides which checks run, how sensitive they are, and what happens when they fire."],
    ["02", "We never silently rewrite model output",
     "Detect, explain with pinned evidence, then allow, log, route to a human, or block. The enterprise always sees what its model actually said."],
    ["03", "Every number is measured or labelled",
     "The prototype produces its own precision, recall, FP/FN rates, latency and regression result. Assumptions carry their formula and inputs."],
  ];
  const cw = (CW - 0.4) / 3;
  items.forEach(([num, head, text], i) => {
    const x = M + i * (cw + 0.2);
    card(s, { x, y, w: cw, h: 2.95 });
    s.addShape(pptx.ShapeType.ellipse, { x: x + 0.28, y: y + 0.28, w: 0.62, h: 0.62,
      fill: { color: NAVY }, line: { width: 0 } });
    s.addText(num, { x: x + 0.28, y: y + 0.4, w: 0.62, h: 0.38, isTextBox: true,
      margin: 0, align: "center", fontFace: HEAD, fontSize: 15, bold: true, color: WHITE });
    s.addText(head, { x: x + 0.28, y: y + 1.06, w: cw - 0.56, h: 0.72, isTextBox: true,
      margin: 0, fontFace: HEAD, fontSize: 15.5, bold: true, color: NAVY, lineSpacing: 19 });
    s.addText(text, { x: x + 0.28, y: y + 1.82, w: cw - 0.56, h: 1.0, isTextBox: true,
      margin: 0, fontFace: BODY, fontSize: 12, color: SLATE, lineSpacing: 16 });
  });
  s.addText("The working prototype runs the whole loop on 294 simulated traces across all three use cases, with no API key and no network.",
    { x: M, y: y + 3.12, w: CW, h: 0.34, isTextBox: true, margin: 0,
      fontFace: BODY, fontSize: 12.5, italic: true, color: MID });
}

/* ───────────────────────── 3 · the portfolio problem ──────────────── */
{
  const s = slide(false);
  let y = title(s, "The problem is the portfolio, not the model", "Problem");
  const cols = [
    ["Customer support assistant", "External · synchronous", "100 ms budget",
     "A wrong answer is a contractual statement to a customer. Blast radius is highest, tolerance for latency lowest."],
    ["Internal knowledge assistant", "Employees · noisy sources", "250 ms budget",
     "Mixed well-governed and loosely governed data. Alert fatigue is the bigger risk than any single wrong answer."],
    ["Decision-support tool", "Regulated workflow", "400 ms budget",
     "The output shapes a decision about a person. Over-flagging is the cheaper error, by a wide margin."],
  ];
  const cw = (CW - 0.44) / 3;
  cols.forEach(([head, sub, budget, text], i) => {
    const x = M + i * (cw + 0.22);
    card(s, { x, y, w: cw, h: 3.5, fill: i === 2 ? "EEF2FC" : PALE });
    s.addText(head, { x: x + 0.3, y: y + 0.3, w: cw - 0.6, h: 0.66, isTextBox: true,
      margin: 0, fontFace: HEAD, fontSize: 16, bold: true, color: NAVY, lineSpacing: 20 });
    s.addText(sub, { x: x + 0.3, y: y + 1.0, w: cw - 0.6, h: 0.28, isTextBox: true,
      margin: 0, fontFace: BODY, fontSize: 11.5, color: SLATE });
    s.addText(budget, { x: x + 0.3, y: y + 1.36, w: cw - 0.6, h: 0.36, isTextBox: true,
      margin: 0, fontFace: HEAD, fontSize: 15, bold: true, color: AMBER });
    s.addText(text, { x: x + 0.3, y: y + 1.84, w: cw - 0.6, h: 1.4, isTextBox: true,
      margin: 0, fontFace: BODY, fontSize: 12.5, color: INK, lineSpacing: 17 });
  });
  s.addText("One checker across all three is too slow for the first, too noisy for the second, and too shallow for the third.",
    { x: M, y: y + 3.72, w: CW, h: 0.36, isTextBox: true, margin: 0,
      fontFace: HEAD, fontSize: 15, bold: true, color: NAVY });
}

/* ───────────────────── 4 · why this is hard ───────────────────────── */
{
  const s = slide(false);
  let y = title(s, "Four things that make this genuinely hard", "Why current approaches fall short");
  const grid = [
    ["The risk families overlap",
     "A fabricated detail about a named person is a hallucination and a privacy exposure at once. Forcing one category loses the second risk or double-counts the incident."],
    ["There is no real-time ground truth",
     "The same knowledge gap that causes a hallucination blocks its verification. Checkers promising to tell you whether a claim is true are promising something they cannot deliver."],
    ["One threshold cannot serve one company",
     "Over-flagging teaches users to click through warnings; under-flagging creates liability. The trade-off must be tuned per use case, and most tooling makes it invisible."],
    ["Enterprises cannot see inside the model",
     "A foundation model consumed over an API offers logits at best. Any checker has to work at the input/output layer, on prompt, retrieval, tool calls and response."],
  ];
  const cw = (CW - 0.28) / 2, ch = 1.62;
  grid.forEach(([head, text], i) => {
    const x = M + (i % 2) * (cw + 0.28);
    const yy = y + Math.floor(i / 2) * (ch + 0.28);
    card(s, { x, y: yy, w: cw, h: ch });
    s.addShape(pptx.ShapeType.ellipse, { x: x + 0.3, y: yy + 0.34, w: 0.34, h: 0.34,
      fill: { color: ICE }, line: { width: 0 } });
    s.addText(String(i + 1), { x: x + 0.3, y: yy + 0.4, w: 0.34, h: 0.24, isTextBox: true,
      margin: 0, align: "center", fontFace: HEAD, fontSize: 11, bold: true, color: NAVY });
    s.addText(head, { x: x + 0.78, y: yy + 0.3, w: cw - 1.1, h: 0.34, isTextBox: true,
      margin: 0, fontFace: HEAD, fontSize: 15, bold: true, color: NAVY });
    s.addText(text, { x: x + 0.78, y: yy + 0.68, w: cw - 1.1, h: 0.84, isTextBox: true,
      margin: 0, fontFace: BODY, fontSize: 12, color: SLATE, lineSpacing: 16 });
  });
}

/* ───────────────────── 5 · competitive layer map ──────────────────── */
{
  const s = slide(false);
  let y = title(s, "Where the gap actually is", "Competition");
  const rows = [
    ["Tracing and storage", "Langfuse · LangSmith · Phoenix · Datadog", "Commoditised. We read from it.", false],
    ["Guardrails and detection", "Bedrock Guardrails · Azure Content Safety · Lakera · NeMo", "Crowded and increasingly free.", false],
    ["Evaluation and scoring", "Braintrust · DeepEval · RAGAS · Galileo · Patronus", "Crowded. A score, not a diagnosis.", false],
    ["Configurable governance across a portfolio", "thin", "Policy is per-application, not a versioned artifact.", false],
    ["Defect lifecycle: priced, owned, closed, regression-tested", "empty", "This is where we build.", true],
  ];
  const rh = 0.78;
  rows.forEach(([layer, who, status, ours], i) => {
    const yy = y + i * (rh + 0.12);
    card(s, { x: M, y: yy, w: CW, h: rh,
      fill: ours ? NAVY : PALE, line: ours ? NAVY : LINE });
    s.addText(layer, { x: M + 0.3, y: yy + 0.13, w: 4.1, h: 0.54, isTextBox: true,
      margin: 0, valign: "middle", fontFace: HEAD, fontSize: 13, bold: true,
      color: ours ? WHITE : NAVY, lineSpacing: 16 });
    s.addText(who, { x: M + 4.5, y: yy + 0.13, w: 4.3, h: 0.54, isTextBox: true,
      margin: 0, valign: "middle", fontFace: BODY, fontSize: 11.5,
      color: ours ? ICE : SLATE, lineSpacing: 15 });
    s.addText(status, { x: M + 8.95, y: yy + 0.13, w: CW - 9.25, h: 0.54, isTextBox: true,
      margin: 0, valign: "middle", fontFace: BODY, fontSize: 11.5, bold: ours,
      color: ours ? WHITE : INK, lineSpacing: 15 });
  });
  s.addText("Anyone can detect a PII leak. Almost nobody turns forty leaks into one owned, priced defect, carries the human's decision into a versioned contract, then proves with a regression run that it worked — and says what it cost.",
    { x: M, y: y + 5 * (rh + 0.12) + 0.12, w: CW, h: 0.5, isTextBox: true, margin: 0,
      fontFace: BODY, fontSize: 12.5, italic: true, color: MID, lineSpacing: 17 });
}

/* ───────────────────────── 6 · architecture ───────────────────────── */
{
  const s = slide(false);
  let y = title(s, "Two lanes, one action, a loop that closes", "Solution and architecture");
  const steps = [
    ["FAST LANE", "deterministic · inline · 100% of traffic\nPII with checksum validation · deny lists · loop and budget breakers", NAVY, WHITE],
    ["SLOW LANE", "semantic · asynchronous · never blocks the user\ngrounding · counterfactual bias screen · explanation policy", MID, WHITE],
    ["FUSION", "every label recorded, one strictest action taken", ICE, NAVY],
    ["DEFECT", "clustered by failure signature · priced · evidence-pinned", ICE, NAVY],
    ["HUMAN", "a reviewer confirms or rejects — nothing moves without this", ICE, NAVY],
    ["CONTRACT", "versioned, content-hashed, git-diffable configuration change", ICE, NAVY],
    ["REGRESSION", "re-run the defect's own traces; report benefit AND cost", ICE, NAVY],
  ];
  const rh = 0.52;
  steps.forEach(([label, text, fill, fg], i) => {
    const yy = y + i * (rh + 0.09);
    s.addShape(pptx.ShapeType.roundRect, { x: M, y: yy, w: 2.05, h: rh, rectRadius: 0.06,
      fill: { color: fill }, line: { width: 0 } });
    s.addText(label, { x: M, y: yy, w: 2.05, h: rh, isTextBox: true, margin: 0,
      align: "center", valign: "middle", fontFace: BODY, fontSize: 11.5, bold: true,
      color: fg, charSpacing: 1 });
    s.addText(text, { x: M + 2.25, y: yy, w: CW - 2.25, h: rh, isTextBox: true,
      margin: 0, valign: "middle", fontFace: BODY, fontSize: 11.5, color: INK,
      lineSpacing: 15 });
  });
  const yy = y + 7 * (rh + 0.09) + 0.14;
  s.addText([
    { text: "Why two lanes.  ", options: { bold: true, color: NAVY } },
    { text: "Blocking a customer-facing response must be cheap, deterministic and defensible. Judging groundedness is none of those. Measured Fast Lane compute is p95 under 0.05 ms against a 100 ms contract budget." },
  ], { x: M, y: yy, w: CW, h: 0.5, isTextBox: true, margin: 0, fontFace: BODY,
    fontSize: 12.5, color: INK, lineSpacing: 17 });
}

/* ─────────────────── 7 · the Evaluation Contract ──────────────────── */
{
  const s = slide(false);
  let y = title(s, "The Evaluation Contract is the product", "Governance");
  const half = (CW - 0.34) / 2;
  card(s, { x: M, y, w: half, h: 3.62, fill: INK, line: INK });
  s.addText("contracts/use_cases/decision_support.yaml", { x: M + 0.3, y: y + 0.26,
    w: half - 0.6, h: 0.26, isTextBox: true, margin: 0, fontFace: "Courier New",
    fontSize: 10, color: "8FA6D8" });
  s.addText(
`use_case: decision_support
risk_level: very_high
latency_budget_ms: 400

detectors:
  pii:           { mode: "strict"   }
  hallucination: { mode: "standard" }
  bias:          { mode: "standard" }
  policy:        { mode: "standard" }

actions:
  high:   block
  medium: human_review
  low:    human_review`,
    { x: M + 0.3, y: y + 0.62, w: half - 0.6, h: 2.9, isTextBox: true, margin: 0,
      fontFace: "Courier New", fontSize: 10.5, color: ICE, lineSpacing: 15.5 });

  const x2 = M + half + 0.34;
  const notes = [
    ["A ratchet, not an override", "A policy pack may raise a detector's strictness or an action's severity — never lower it. A team cannot configure its way out of a regulatory floor."],
    ["Content-hashed", "customer_support@r2-5ae442dedc. Two contracts that behave identically share a version; any edit produces a new one, and every audit record names it."],
    ["The jurisdiction decides what is high risk", "Not the team. The EU pack names its own high-risk use cases, so a support chatbot never inherits Annex III obligations by accident."],
  ];
  let yy = y;
  notes.forEach(([head, text]) => {
    s.addText(head, { x: x2, y: yy, w: half, h: 0.3, isTextBox: true, margin: 0,
      fontFace: HEAD, fontSize: 15, bold: true, color: NAVY });
    s.addText(text, { x: x2, y: yy + 0.34, w: half, h: 0.76, isTextBox: true, margin: 0,
      fontFace: BODY, fontSize: 12.5, color: SLATE, lineSpacing: 17 });
    yy += 1.2;
  });
  s.addText("Regulatory requirements are policy configuration, not application logic.",
    { x: M, y: y + 3.84, w: CW, h: 0.36, isTextBox: true, margin: 0,
      fontFace: HEAD, fontSize: 16, bold: true, color: NAVY });
}

/* ─────────────── 8 · three use cases, three configurations ────────── */
{
  const s = slide(false);
  let y = title(s, "The same platform, configured three ways", "Use cases");
  table(s, ["", "Customer support", "Internal knowledge", "Decision support"], [
    ["Risk posture", "High", "Medium", "Very high"],
    ["Latency budget", "100 ms", "250 ms", "400 ms"],
    ["PII", "standard → strict in EU", "standard → strict in EU", "strict"],
    ["Hallucination", "standard", "permissive — deliberately", "standard → strict in EU"],
    ["Bias", "off — no decisions on people", "off", "standard → strict in EU"],
    ["Policy", "standard", "standard", "standard → strict in US"],
    ["High severity →", "block", "human review", "block"],
  ], { x: M, y, w: CW, colW: [2.3, 3.25, 3.25, 3.26], rowH: 0.42, fs: 12, boldFirst: true });
  s.addText([
    { text: "The permissive setting on the internal assistant is a deliberate governance choice, not an oversight. ", options: { bold: true, color: NAVY } },
    { text: "The blast radius is an employee who can sanity-check the answer, and alert fatigue is the larger risk. The prototype measures exactly what that choice costs." },
  ], { x: M, y: y + 3.5, w: CW, h: 0.6, isTextBox: true, margin: 0,
    fontFace: BODY, fontSize: 12.5, color: INK, lineSpacing: 17 });
}

/* ──────────────── 9 · jurisdictions ───────────────────────────────── */
{
  const s = slide(false);
  let y = title(s, "Same 264 traces, three policy packs, zero code changes", "Configurable governance");

  // Stacked bars drawn as shapes: no chart engine, so nothing can fail to render.
  const segs = [
    { key: "allow",        color: "C9D6EE", fg: NAVY  },
    { key: "log",          color: "8FA6D8", fg: WHITE },
    { key: "human review", color: AMBER,    fg: WHITE },
    { key: "block",        color: NAVY,     fg: WHITE },
  ];
  const data = [
    ["India",          { allow: 121, log: 12, "human review": 42, block: 89  }],
    ["European Union", { allow: 121, log: 7,  "human review": 24, block: 112 }],
    ["United States",  { allow: 121, log: 12, "human review": 42, block: 89  }],
  ];
  const TOTAL = 264, BARX = M + 1.95, BARW = 6.5, BH = 0.62;
  data.forEach(([label, row], i) => {
    const yy = y + 0.3 + i * (BH + 0.42);
    s.addText(label, { x: M, y: yy, w: 1.9, h: BH, isTextBox: true, margin: 0,
      valign: "middle", align: "right", fontFace: BODY, fontSize: 13,
      bold: label === "European Union", color: label === "European Union" ? NAVY : INK });
    let cx = BARX;
    segs.forEach((seg) => {
      const w = (row[seg.key] / TOTAL) * BARW;
      s.addShape(pptx.ShapeType.rect, { x: cx, y: yy, w, h: BH,
        fill: { color: seg.color }, line: { color: WHITE, width: 1 } });
      if (w > 0.42) {
        s.addText(String(row[seg.key]), { x: cx, y: yy, w, h: BH, isTextBox: true,
          margin: 0, align: "center", valign: "middle", fontFace: BODY,
          fontSize: 11.5, bold: true, color: seg.fg });
      }
      cx += w;
    });
  });
  const legY = y + 0.3 + 3 * (BH + 0.42) + 0.06;
  let lx = BARX;
  segs.forEach((seg) => {
    s.addShape(pptx.ShapeType.rect, { x: lx, y: legY + 0.05, w: 0.2, h: 0.2,
      fill: { color: seg.color }, line: { width: 0 } });
    s.addText(seg.key, { x: lx + 0.28, y: legY, w: 1.5, h: 0.3, isTextBox: true,
      margin: 0, valign: "middle", fontFace: BODY, fontSize: 11, color: SLATE });
    lx += 1.68;
  });

  const x2 = M + 8.75;
  card(s, { x: x2, y, w: CW - 8.75, h: 2.92 });
  s.addText("What changed", { x: x2 + 0.28, y: y + 0.24, w: CW - 9.31, h: 0.3,
    isTextBox: true, margin: 0, fontFace: HEAD, fontSize: 15, bold: true, color: NAVY });
  bullets(s, [
    "EU raises PII to strict everywhere",
    "High-severity moves from human review to block, citing Article 22",
    "Any bias finding is forced to human oversight",
  ], { x: x2 + 0.28, y: y + 0.66, w: CW - 9.31, h: 2.0, size: 11.5, color: INK });
  stat(s, { x: x2, y: y + 3.2, w: CW - 8.75, value: "+23 blocks",
    label: "in the EU, on identical traces and identical code", size: 26, color: AMBER });
}

/* ─────────────────── 10 · measured results ────────────────────────── */
{
  const s = slide(false);
  let y = title(s, "Measured — including where we lose", "Prototype evidence");
  const half = (CW - 0.34) / 2;
  s.addText("Generated corpus · 264 traces", { x: M, y, w: half, h: 0.3, isTextBox: true,
    margin: 0, fontFace: BODY, fontSize: 11.5, bold: true, color: SLATE, charSpacing: 0.8 });
  table(s, ["Risk family", "Precision", "Recall"], [
    ["Privacy", "0.957", "1.000"], ["Hallucination", "0.965", "0.887"],
    ["Bias", "1.000", "1.000"], ["Policy", "0.800", "1.000"],
    ["Behaviour", "1.000", "1.000"],
  ], { x: M, y: y + 0.36, w: half, colW: [2.7, 1.85, 1.85], rowH: 0.38, fs: 12 });

  const x2 = M + half + 0.34;
  s.addText("Hand-written adversarial holdout · 30 traces", { x: x2, y, w: half, h: 0.3,
    isTextBox: true, margin: 0, fontFace: BODY, fontSize: 11.5, bold: true,
    color: SLATE, charSpacing: 0.8 });
  table(s, ["Risk family", "Precision", "Recall"], [
    ["Privacy", "1.000", "1.000"], ["Hallucination", "0.857", "0.750"],
    ["Bias", "1.000", "1.000"], ["Policy", "1.000", "1.000"],
    ["Behaviour", "n/a", "n/a"],
  ], { x: x2, y: y + 0.36, w: half, colW: [2.7, 1.85, 1.85], rowH: 0.38, fs: 12 });

  const yy = y + 2.8;
  card(s, { x: M, y: yy, w: CW, h: 1.36, fill: "FDF6EC", line: "F0DFC4" });
  s.addText("The holdout was written by hand after the detectors, to test the risk rather than the templates.",
    { x: M + 0.34, y: yy + 0.2, w: CW - 0.68, h: 0.3, isTextBox: true, margin: 0,
      fontFace: HEAD, fontSize: 14.5, bold: true, color: AMBER });
  s.addText("Hallucination recall drops to 0.75 there. The gap is one specific class — open-ended fabrication with no figure to contradict, like an invented loyalty tier. Our offline judge is built around figures, which is exactly what the optional LLM-judge adapter is for. We would rather show the hole than have it found.",
    { x: M + 0.34, y: yy + 0.56, w: CW - 0.68, h: 0.66, isTextBox: true, margin: 0,
      fontFace: BODY, fontSize: 12.5, color: INK, lineSpacing: 17 });
  s.addText("Fast Lane p95 under 0.05 ms of detector compute  ·  100 ms contract budget  ·  reproducible with no API key and no network",
    { x: M, y: yy + 1.5, w: CW, h: 0.3, isTextBox: true, margin: 0,
      fontFace: BODY, fontSize: 12, italic: true, color: SLATE });
}

/* ─────────────── 11 · the trade-off we are choosing ───────────────── */
{
  const s = slide(false);
  let y = title(s, "We do not solve the trade-off. We price it.", "False positives vs false negatives");
  s.addText("PII detector, customer support: what each confidence threshold buys, and what it costs",
    { x: M, y: y - 0.14, w: CW, h: 0.3, isTextBox: true, margin: 0,
      fontFace: BODY, fontSize: 12.5, color: SLATE });

  const ths = [
    [0.35, 0.923, 1.0], [0.45, 0.923, 1.0], [0.55, 0.923, 1.0], [0.65, 0.923, 1.0],
    [0.75, 1.0, 0.208], [0.85, 1.0, 0.208], [0.95, 1.0, 0.208],
  ];
  const PX = M + 0.7, PY = y + 0.78, PW = 7.6, PH = 2.72, GW = PW / ths.length;
  // baseline + gridlines
  [0, 0.5, 1.0].forEach((v) => {
    const gy = PY + PH - v * PH;
    s.addShape(pptx.ShapeType.line, { x: PX - 0.5, y: gy, w: PW + 0.5, h: 0,
      line: { color: v === 0 ? "C4CCE0" : "EDF1F9", width: v === 0 ? 1 : 0.75 } });
    s.addText(v.toFixed(1), { x: PX - 1.0, y: gy - 0.13, w: 0.45, h: 0.26, isTextBox: true,
      margin: 0, align: "right", valign: "middle", fontFace: BODY, fontSize: 10, color: SLATE });
  });
  ths.forEach(([th, prec, rec], i) => {
    const gx = PX + i * GW;
    const bw = (GW - 0.22) / 2;
    [[prec, NAVY], [rec, AMBER]].forEach(([v, c], k) => {
      const bh = v * PH;
      s.addShape(pptx.ShapeType.rect, { x: gx + 0.08 + k * bw, y: PY + PH - bh,
        w: bw - 0.04, h: bh, fill: { color: c }, line: { width: 0 } });
      // Label inside the bar: a label above the bar collides with the legend
      // whenever the value is at the top of the scale.
      const inside = bh > 0.4;
      s.addText(v.toFixed(2).replace("0.", "."), {
        x: gx + 0.02 + k * bw, y: inside ? PY + PH - bh + 0.06 : PY + PH - bh - 0.26,
        w: bw + 0.06, h: 0.24, isTextBox: true, margin: 0, align: "center",
        fontFace: BODY, fontSize: 9.5, bold: true, color: inside ? WHITE : c });
    });
    s.addText(th.toFixed(2), { x: gx, y: PY + PH + 0.06, w: GW, h: 0.26, isTextBox: true,
      margin: 0, align: "center", fontFace: BODY, fontSize: 10.5,
      bold: th === 0.75, color: th === 0.75 ? AMBER : SLATE });
  });
  s.addText("confidence threshold", { x: PX, y: PY + PH + 0.34, w: 3.6, h: 0.26,
    isTextBox: true, margin: 0, fontFace: BODY, fontSize: 10.5, color: SLATE });
  [["Precision", NAVY], ["Recall", AMBER]].forEach(([t, c], i) => {
    const lx = PX + 4.6 + i * 1.5;
    s.addShape(pptx.ShapeType.rect, { x: lx, y: PY + PH + 0.36, w: 0.2, h: 0.2,
      fill: { color: c }, line: { width: 0 } });
    s.addText(t, { x: lx + 0.28, y: PY + PH + 0.31, w: 1.2, h: 0.3, isTextBox: true,
      margin: 0, valign: "middle", fontFace: BODY, fontSize: 11, color: SLATE });
  });

  const x2 = M + 8.7;
  s.addText("Push the threshold past 0.65 and precision reaches 1.000 — while recall collapses from 1.000 to 0.208. Four in five real leaks walk past.",
    { x: x2, y: PY - 0.24, w: CW - 8.7, h: 1.0, isTextBox: true, margin: 0,
      fontFace: BODY, fontSize: 13, color: INK, lineSpacing: 18 });
  s.addText("That is not a bug to fix. It is the decision the contract exists to record — and a governance owner should see its price before signing, not after an incident.",
    { x: x2, y: PY + 0.92, w: CW - 8.7, h: 1.1, isTextBox: true, margin: 0,
      fontFace: BODY, fontSize: 13, color: INK, lineSpacing: 18 });
  stat(s, { x: x2, y: PY + 2.2, w: CW - 8.7, value: "1.000 → 0.208",
    label: "recall surrendered to buy perfect precision", size: 24, color: AMBER });
}

/* ─────────────── 12 · defect: priced, owned, closable ─────────────── */
{
  const s = slide(false);
  let y = title(s, "Findings become a defect that can be closed", "The lifecycle");
  card(s, { x: M, y, w: CW, h: 1.62 });
  s.addText("DEF-EA14BE", { x: M + 0.34, y: y + 0.24, w: 2.2, h: 0.32, isTextBox: true,
    margin: 0, fontFace: "Courier New", fontSize: 13, bold: true, color: AMBER });
  s.addText("Response restates a governed figure incorrectly", { x: M + 2.7, y: y + 0.2,
    w: 6.4, h: 0.4, isTextBox: true, margin: 0, fontFace: HEAD, fontSize: 17,
    bold: true, color: NAVY });
  s.addText("Root cause: the system prompt does not require the answer to quote the retrieved policy. 16 occurrences in 114 customer-support traces.",
    { x: M + 2.7, y: y + 0.66, w: 6.6, h: 0.6, isTextBox: true, margin: 0,
      fontFace: BODY, fontSize: 12.5, color: SLATE, lineSpacing: 17 });
  stat(s, { x: M + 9.6, y: y + 0.3, w: CW - 9.94, value: "₹3.55L", align: "right",
    label: "estimated cost per month", size: 34, labelColor: SLATE });

  const yy = y + 1.86;
  s.addText("rate 16/114 = 0.1404  ×  12,000 interactions/week  ×  4.33 weeks  =  7,293 occurrences/month  ×  (₹14 rework + 0.07 × ₹95 handoff + ₹28 churn exposure)",
    { x: M, y: yy, w: CW, h: 0.52, isTextBox: true, margin: 0,
      fontFace: "Courier New", fontSize: 10.5, color: MID, lineSpacing: 15 });
  s.addText("Every input is published, and printed beside the figure. Disagree with the ₹95 handoff cost and one line in the contract changes the number.",
    { x: M, y: yy + 0.58, w: CW, h: 0.3, isTextBox: true, margin: 0,
      fontFace: BODY, fontSize: 12, italic: true, color: SLATE });

  const y3 = yy + 1.02;
  const steps = ["Detect", "Cluster + price", "Human confirms", "Contract v2", "Regression", "Audit"];
  const sw = (CW - 5 * 0.16) / 6;
  steps.forEach((t, i) => {
    const x = M + i * (sw + 0.16);
    s.addShape(pptx.ShapeType.roundRect, { x, y: y3, w: sw, h: 0.62, rectRadius: 0.06,
      fill: { color: i === 2 ? NAVY : PALE }, line: { color: i === 2 ? NAVY : LINE, width: 0.75 } });
    s.addText(t, { x, y: y3, w: sw, h: 0.62, isTextBox: true, margin: 0, align: "center",
      valign: "middle", fontFace: BODY, fontSize: 12, bold: i === 2,
      color: i === 2 ? WHITE : NAVY });
  });
  s.addText("Nothing changes without the human step. The contract change is versioned, and the regression set is the defect's own traces — so the test cannot drift away from the failure.",
    { x: M, y: y3 + 0.78, w: CW, h: 0.4, isTextBox: true, margin: 0,
      fontFace: BODY, fontSize: 12.5, color: INK, lineSpacing: 17 });
}

/* ───────────────── 13 · closing the loop, with its cost ───────────── */
{
  const s = slide(false);
  let y = title(s, "The loop closes — and we report the bill", "Measured outcome");
  const cw = (CW - 0.48) / 3;
  const cards = [
    ["6 → 3", "failures reaching the user", "−50% on a 30-trace regression set", GREEN],
    ["2 → 13", "hallucination false positives", "+11 across 114 interactions", AMBER],
    ["60 → 64", "interactions needing a human", "+4 of 114", AMBER],
  ];
  cards.forEach(([v, l, sub, c], i) => {
    const x = M + i * (cw + 0.24);
    card(s, { x, y, w: cw, h: 2.1 });
    s.addText(v, { x: x + 0.3, y: y + 0.28, w: cw - 0.6, h: 0.66, isTextBox: true,
      margin: 0, fontFace: HEAD, fontSize: 36, bold: true, color: c });
    s.addText(l, { x: x + 0.3, y: y + 1.0, w: cw - 0.6, h: 0.34, isTextBox: true,
      margin: 0, fontFace: BODY, fontSize: 13.5, bold: true, color: NAVY });
    s.addText(sub, { x: x + 0.3, y: y + 1.38, w: cw - 0.6, h: 0.4, isTextBox: true,
      margin: 0, fontFace: BODY, fontSize: 11.5, color: SLATE, lineSpacing: 15 });
  });
  const yy = y + 2.34;
  card(s, { x: M, y: yy, w: CW, h: 1.5, fill: INK, line: INK });
  s.addText("customer_support@r1-b7cc3c4d4f   →   customer_support@r2-5ae442dedc",
    { x: M + 0.34, y: yy + 0.22, w: CW - 0.68, h: 0.3, isTextBox: true, margin: 0,
      fontFace: "Courier New", fontSize: 12.5, color: ICE });
  s.addText("The fix is one line: grounding_required becomes true, so the assistant must refuse rather than improvise when the corpus does not cover the question. In Round 1 this slide carried a −94%. It was not measured, so it is gone. This one is, and it comes with its cost.",
    { x: M + 0.34, y: yy + 0.6, w: CW - 0.68, h: 0.74, isTextBox: true, margin: 0,
      fontFace: BODY, fontSize: 13, color: WHITE, lineSpacing: 18 });
}

/* ─────────────────────── 14 · target users ────────────────────────── */
{
  const s = slide(false);
  let y = title(s, "Who buys, who approves, who uses it", "Target users");
  const rows = [
    ["Head of AI / platform engineering", "economic buyer", "Several AI systems in production, no consistent way to govern them", "One control plane across the portfolio; per-use-case configuration without per-use-case code"],
    ["Risk, compliance and the DPO", "approver", "Must attest to controls they cannot inspect", "Versioned contracts citing the specific regulation, a hash-chained audit trail, human approval in the loop"],
    ["Application engineer", "daily user", "Told 'the assistant is wrong sometimes' with no reproduction", "A defect with a root cause, example traces, evidence spans and a regression set"],
    ["Internal and external audit", "verifier", "Screenshots and a policy document", "A chain of records that cannot be edited after the fact"],
  ];
  const rh = 0.86;
  rows.forEach(([who, role, problem, gets], i) => {
    const yy = y + i * (rh + 0.14);
    card(s, { x: M, y: yy, w: CW, h: rh });
    s.addText(who, { x: M + 0.3, y: yy + 0.12, w: 3.3, h: 0.34, isTextBox: true,
      margin: 0, fontFace: HEAD, fontSize: 13.5, bold: true, color: NAVY });
    s.addText(role, { x: M + 0.3, y: yy + 0.46, w: 3.3, h: 0.26, isTextBox: true,
      margin: 0, fontFace: BODY, fontSize: 11, italic: true, color: AMBER });
    s.addText(problem, { x: M + 3.8, y: yy + 0.16, w: 3.6, h: 0.58, isTextBox: true,
      margin: 0, valign: "middle", fontFace: BODY, fontSize: 11.5, color: SLATE, lineSpacing: 15 });
    s.addText(gets, { x: M + 7.6, y: yy + 0.16, w: CW - 7.9, h: 0.58, isTextBox: true,
      margin: 0, valign: "middle", fontFace: BODY, fontSize: 11.5, color: INK, lineSpacing: 15 });
  });
  s.addText("Initial focus: Indian financial services and regulated SaaS — DPDP obligations today, EU AI Act exposure by August 2026, and several AI use cases already live.",
    { x: M, y: y + 4 * (rh + 0.14) + 0.08, w: CW, h: 0.36, isTextBox: true, margin: 0,
      fontFace: BODY, fontSize: 12.5, italic: true, color: MID });
}

/* ───────────────────── 15 · business model + roadmap ──────────────── */
{
  const s = slide(false);
  let y = title(s, "Land read-only, then earn the inline path", "Business model and roadmap");
  const phases = [
    ["Phase 1", "0–3 months", "Read-only", "Ingest from the tracing layer they already run. Slow Lane only, nothing inline, nothing blocked. First priced defect register."],
    ["Phase 2", "3–6 months", "Contracts + Fast Lane", "Author contracts with their risk team. Deterministic Fast Lane inline behind a kill switch. First two policy packs."],
    ["Phase 3", "6–12 months", "Close the loop", "Human resolution queue, contracts in their own git, automatic regression sets, a CI gate on their deploy pipeline."],
    ["Phase 4", "12–24 months", "Portfolio", "Multi-use-case rollout, jurisdiction packs as a subscription, shadow-call bias screening, a managed LLM-judge tier."],
  ];
  const cw = (CW - 0.54) / 4;
  phases.forEach(([p, when, head, text], i) => {
    const x = M + i * (cw + 0.18);
    card(s, { x, y, w: cw, h: 2.9, fill: i === 0 ? "EEF2FC" : PALE });
    s.addText(p, { x: x + 0.28, y: y + 0.26, w: cw - 0.56, h: 0.3, isTextBox: true,
      margin: 0, fontFace: BODY, fontSize: 11, bold: true, color: AMBER, charSpacing: 1.2 });
    s.addText(when, { x: x + 0.28, y: y + 0.56, w: cw - 0.56, h: 0.26, isTextBox: true,
      margin: 0, fontFace: BODY, fontSize: 11, color: SLATE });
    s.addText(head, { x: x + 0.28, y: y + 0.9, w: cw - 0.56, h: 0.6, isTextBox: true,
      margin: 0, fontFace: HEAD, fontSize: 15, bold: true, color: NAVY, lineSpacing: 19 });
    s.addText(text, { x: x + 0.28, y: y + 1.52, w: cw - 0.56, h: 1.2, isTextBox: true,
      margin: 0, fontFace: BODY, fontSize: 11.5, color: INK, lineSpacing: 16 });
  });
  const yy = y + 3.14;
  s.addText([
    { text: "Pricing.  ", options: { bold: true, color: NAVY } },
    { text: "Platform subscription by governed interaction volume: $30k–150k ACV for an enterprise running 3–8 AI use cases. The buyer's comparison is not a cheaper tool — it is the compliance headcount reading traces by hand, plus the exposure of the failures nobody is reading." },
  ], { x: M, y: yy, w: CW, h: 0.6, isTextBox: true, margin: 0, fontFace: BODY,
    fontSize: 12.5, color: INK, lineSpacing: 17 });
}

/* ───────────────────── 16 · risks and mitigations ─────────────────── */
{
  const s = slide(false);
  let y = title(s, "What could go wrong, and what we do about it", "Risks and mitigations");
  const grid = [
    ["Detection commoditises", "Model providers ship guardrails free", "We do not sell detection. Detectors are pluggable; the contract, the lifecycle and the audit chain are the product."],
    ["Alert fatigue", "Over-flagging is how these tools die", "The trade-off is measured per threshold before a contract is signed, and review load is reported with every change."],
    ["The bias screen is over-read", "'The tool said it's biased' is a headline risk", "Framed as a screening signal for human review everywhere it appears — in code, in the UI and in the report."],
    ["The judge misses open fabrication", "Measured: 0.75 recall on the holdout", "Reported, not hidden. The LLM-judge adapter is built, and this class is what it is for."],
    ["Cost figures are challenged", "They are assumptions", "Every input is in one file, printed beside every figure, and changeable by the buyer."],
    ["We become a single point of failure", "A control plane that fails closed takes production down", "Fast Lane fails open with an audit record; the judge falls back to the offline path rather than erroring."],
  ];
  const cw = (CW - 0.28) / 2, ch = 1.34;
  grid.forEach(([head, why, fix], i) => {
    const x = M + (i % 2) * (cw + 0.28);
    const yy = y + Math.floor(i / 2) * (ch + 0.2);
    card(s, { x, y: yy, w: cw, h: ch });
    s.addText(head, { x: x + 0.28, y: yy + 0.18, w: cw - 0.56, h: 0.3, isTextBox: true,
      margin: 0, fontFace: HEAD, fontSize: 14, bold: true, color: NAVY });
    s.addText(why, { x: x + 0.28, y: yy + 0.5, w: cw - 0.56, h: 0.26, isTextBox: true,
      margin: 0, fontFace: BODY, fontSize: 11, italic: true, color: AMBER });
    s.addText(fix, { x: x + 0.28, y: yy + 0.78, w: cw - 0.56, h: 0.48, isTextBox: true,
      margin: 0, fontFace: BODY, fontSize: 11.5, color: SLATE, lineSpacing: 15 });
  });
}

/* ─────────────────────────── 17 · close ───────────────────────────── */
{
  const s = slide(true);
  s.addShape(pptx.ShapeType.roundRect, { x: 7.6, y: -2.2, w: 8.6, h: 8.6,
    rectRadius: 0.5, fill: { color: NAVY, transparency: 66 }, line: { width: 0 } });
  s.addText("Turn every AI failure into a better control —\nand be able to prove it held.",
    { x: M, y: 2.35, w: 11.4, h: 1.7, isTextBox: true, margin: 0, fontFace: HEAD,
      fontSize: 38, bold: true, color: WHITE, lineSpacing: 46 });
  s.addText("Anyone can flag a PII leak. Almost nobody turns forty of them into one owned, priced defect, carries a human's decision into a versioned contract, and then proves with a regression run that the fix worked — and tells you what it cost.",
    { x: M, y: 4.3, w: 9.6, h: 1.1, isTextBox: true, margin: 0, fontFace: BODY,
      fontSize: 15, color: ICE, lineSpacing: 24 });
  s.addText("github.com/omchaudhar/mycroft-ai   ·   bash run.sh   ·   no API key, no network",
    { x: M, y: 6.2, w: 11.4, h: 0.34, isTextBox: true, margin: 0, fontFace: "Courier New",
      fontSize: 12.5, color: "9FB2D8" });
}

pptx.writeFile({ fileName: OUT }).then(() => console.log("wrote " + OUT));
