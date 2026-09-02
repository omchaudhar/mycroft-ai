# Prototype video — brief for whoever records it

**You do not need to know this project.** Follow this page top to bottom.
Two segments, about 3 minutes total, and the first one drives itself.

- **Segment A — terminal (73 seconds, self-driving).** One command. It paces
  itself for narration; you do not touch the keyboard once it starts.
- **Segment B — the app (~90 seconds, 6 clicks).** Every click is listed.

Read the narration in your own words. It is written to be spoken, not read out
verbatim, and nothing in it depends on hitting an exact second.

---

## 1. Setup — once, about 5 minutes

```bash
git clone https://github.com/omchaudhar/mycroft-ai && cd mycroft-ai
```

```bash
python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt
```

```bash
./.venv/bin/python data/generate.py && ./.venv/bin/python -m data.holdout && ./.venv/bin/python scripts/run_eval.py
```

No API key and no internet are needed after that install. If the third command
prints a table of precision and recall numbers, you are ready.

**Before recording:**

- Terminal at a **large font** — 16–18 pt. It will be watched on a laptop.
- Terminal window about **90 columns wide**; the output is formatted for 78.
- Close Slack, mail, and anything that shows notifications.
- Rehearse once at double speed: `./.venv/bin/python scripts/record_demo.py --speed 2`

---

## 2. Segment A — the terminal (73 seconds)

Start recording, then run:

```bash
./.venv/bin/python scripts/record_demo.py
```

It prints seven sections and pauses between them. Talk over it. If you fall
behind, stop worrying about matching — the pacing is generous.

| Section appears | Say something like |
|---|---|
| **1 · A failure reaches a customer** | "A support assistant answering a refund question. It sounds fine. The retrieved policy says seven to ten working days. The response says five." |
| **2 · Two lanes, one action** | "Two lanes check it. The Fast Lane is deterministic and runs inline on every interaction — that's a third of a millisecond. The Slow Lane is semantic and runs asynchronously, so it never sits between the user and their answer. The finding is pinned to evidence: what the response said, and the exact policy sentence it contradicts. Action: block." |
| **3 · Three jurisdictions** | "Same trace, same code, three policy packs. India sends it to human review. The EU blocks it — because the EU pack raises the high-severity action from review to block, citing Article 22. Regulation as configuration, not as an if-statement." |
| **4 · One priced defect** | "Sixteen traces, one defect, one root cause. And a price — about three and a half lakh a month. That number isn't invented: it's the measured occurrence rate times assumptions that are printed right underneath it and that anyone can change." |
| **5 · A human decides** | "A reviewer confirms it. That writes a versioned contract change — one flag flips, and the contract gets a new content hash." |
| **6 · The regression** | "Then we re-run the defect's own traces. Failures reaching the user halve, six to three. And it costs eleven false positives and four extra human reviews out of a hundred and fourteen. We report the bill every time." |
| **7 · The audit chain** | "Every step is one record, each carrying the hash of the one before it. Not a log — a chain. It verifies live, and it can't be edited after the fact." |

When it prints the closing line, **pause for two seconds** before moving on.

---

## 3. Segment B — the app (~90 seconds)

Leave the recording running. In a second terminal:

```bash
./.venv/bin/python -m streamlit run app/streamlit_app.py
```

Wait for the browser to open at `http://localhost:8501`, then switch the
recording to that window. **Six clicks, in this order:**

**1. Live tab.** In the *Trace* dropdown, pick any entry whose label contains
`hallucination`.

> "Here it is as a product. The action, the two lane timings, and the evidence
> — response on one side, source on the other."

**2. Scroll to the bottom of the Live tab** — the table titled *The same trace
under every policy pack*.

> "The same trace under all three jurisdictions, computed live. No code changed
> between those rows."

**3. Trace dropdown again** — pick an entry whose label contains
`hallucination, privacy` (two labels).

> "The brief calls this one out specifically: a fabricated detail about a person
> is a hallucination and a privacy leak at once. We record both labels and take
> one action — the strictest one any finding demands."

**4. Evaluation Contract tab.** Change **pii** from `standard` to `strict`.

> "This is the contract. Change one setting and watch the version hash change,
> and the decisions move across a hundred and fourteen traces. The table below
> shows what the change buys and what it costs — both directions."

**5. Defects tab.** Pick **DEF-EA14BE** from the dropdown.

> "Sixteen traces, one owned defect, with the pricing formula printed underneath."

**6. Click "Accept, update the contract, run the regression."** Wait ~5 seconds.

> "A human accepts it. That produces a contract diff you can read, and the
> regression: six escapes down to three, at the cost of eleven false positives.
> That's the whole trade, stated in both directions."

Stop the recording.

---

## 4. Closing line

If you want a spoken outro over the final frame:

> "Anyone can flag a PII leak. Almost nobody turns forty of them into one owned,
> priced defect, carries a human's decision into a versioned contract, and then
> proves with a regression run that the fix worked — and says what it cost."

---

## 5. Recording and uploading

**macOS.** Press `Cmd + Shift + 5` → *Record Entire Screen* → click **Options**
and pick your microphone (it defaults to none) → **Record**. Stop from the menu
bar. The file lands on the Desktop as a `.mov`.

**Windows.** `Win + Alt + R` (Xbox Game Bar), or OBS if you have it.

**Then:**

1. Upload to Google Drive.
2. Right-click the file → **Share** → change *Restricted* to **Anyone with the
   link** → **Viewer**.
3. Copy the link and paste it into the submission form's video field, and onto
   the video slide of the deck.

**Do not skip step 2.** A private link is the single most common way a
submission video fails to be viewable by judges.

---

## 6. Before you send it

- [ ] Audio is audible the whole way through — play back the first 20 seconds
- [ ] Terminal text is readable at normal playback size
- [ ] No notifications, no personal tabs, no email visible
- [ ] The regression numbers appear on screen (6 → 3, and the false-positive cost)
- [ ] The Drive link is set to *anyone with the link*
- [ ] You opened that link in a private browser window and it played

---

## If something goes wrong

**The demo script errors.** Run the three setup commands again — the corpus
files it reads are generated, not committed.

**Streamlit does not open.** It is slow the first time. Give it 15 seconds,
then open `http://localhost:8501` by hand.

**The pacing feels too slow or too fast.** `--speed 1.4` is a touch quicker,
`--speed 0.8` slower. `--speed 0` removes all pauses, for a silent rehearsal.

**Numbers on screen differ from this page.** They are computed live and should
match exactly. If they do not, run `./.venv/bin/python scripts/run_eval.py` and
narrate what is actually on screen — never what is written here.
