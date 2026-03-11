# Step 4 — Input Sanitization

**Audit finding addressed:** S-12 (no HTML sanitization on report fields)

---

## Purpose

Strip HTML tags from `ManualReport` `title` and `body` fields at the input boundary to prevent stored XSS payloads accumulating in the database, even though React escapes output by default today.

---

## Deliverables

- `code/backend/requirements.txt` — `bleach>=6.0.0` added.
- `code/backend/app/models/manual_report.py` — `strip_html` field validator added to `ManualReportCreate` and `ManualReportUpdate` schemas, applied to `title` and `body`.

---

## Primary files to change

- [code/backend/requirements.txt](code/backend/requirements.txt)
- [code/backend/app/models/manual_report.py](code/backend/app/models/manual_report.py)

---

## Detailed implementation steps

1. **`requirements.txt`** — Add `bleach>=6.0.0` on a new line.

2. **`app/models/manual_report.py`** — Add `import bleach` at the top of the file.

3. **`ManualReportCreate` schema** — Add a Pydantic v2 field validator that strips HTML from `title` and `body`:
   ```python
   @field_validator("title", "body", mode="before")
   @classmethod
   def strip_html(cls, v: object) -> object:
       if isinstance(v, str):
           return bleach.clean(v, tags=[], strip=True)
       return v
   ```
   - `tags=[]` means no HTML tags are allowed — all tags are removed.
   - `strip=True` removes the tags entirely (rather than escaping them as `&lt;b&gt;`).
   - `mode="before"` ensures the sanitized string is what Pydantic validates for length/content constraints.

4. **`ManualReportUpdate` schema** — Apply the same `strip_html` validator with the same signature. Fields in `ManualReportUpdate` are typically `Optional[str]`, so the `isinstance(v, str)` guard handles `None` values safely.

5. **Scope boundary:** Only `ManualReport` fields are in scope for this step. `Task` `title`/`notes` and `SystemState` `description` fields are plain-text fields with no known HTML injection vectors in the current UI. They may be addressed in a follow-up step if the attack surface changes (e.g., a rich-text editor is introduced).

---

## Integration & Edge Cases

- **Markdown content:** `bleach.clean(v, tags=[], strip=True)` only removes HTML tags. Markdown syntax (e.g., `**bold**`, `# heading`, `- list item`) is not affected because those characters are not HTML tags. Existing reports with markdown formatting will render identically after sanitization.
- **Existing data:** Stored reports are not retroactively sanitized. Any HTML in the database before this step remains there. This is acceptable — the fix prevents new injections. A one-time migration to clean existing rows could be a follow-up task.
- **`bleach` and Python 3.12:** `bleach>=6.0.0` supports Python 3.12. Verify with `python -m pip show bleach` after install.
- **`bleach` and `html5lib`:** `bleach` depends on `html5lib`. This will be installed automatically. Confirm it does not conflict with other dependencies.
- **`mode="before"` and `ManualReportUpdate`:** Pydantic v2 runs `mode="before"` validators before type coercion. For `Optional[str]` fields, `None` bypasses the `isinstance(v, str)` guard and passes through unchanged — this is correct behaviour.
- **Word count side effect:** `report_service.py` computes `word_count = len(data.body.split())`. The body passed to the service is already sanitized (HTML stripped) at this point, so the word count reflects clean text. No change needed in `report_service.py`.

---

## Acceptance Criteria

1. `POST /reports` with `title: "<b>hello</b>"` returns 201, and the stored/returned `title` is `"hello"` (tags stripped).
2. `POST /reports` with `body: "<script>alert(1)</script>test"` returns 201, and the stored/returned `body` is `"test"`.
3. `POST /reports` with `title: "**bold** _italic_"` (markdown) returns 201 unchanged — markdown characters are not stripped.
4. `PUT /reports/{id}` with `body: "<p>updated</p>"` returns 200, and the updated `body` is `"updated"`.
5. `PUT /reports/{id}` with `body: null` (if field is optional) returns 200 without error — the `None` value passes through the validator safely.
6. `grep "bleach" code/backend/requirements.txt` finds a match.
7. All existing backend tests pass: `pytest code/backend/tests/ -q` exits 0.

---

## Testing / QA

**Tests to add in `code/backend/tests/test_reports.py`:**

- `test_html_stripped_from_title` — POST a report with `title="<b>hello</b>"`. Assert `response.json()["title"] == "hello"`.
- `test_html_stripped_from_body` — POST a report with `body="<script>xss</script>text"`. Assert `response.json()["body"] == "text"`.
- `test_markdown_preserved_in_body` — POST a report with `body="## heading\n- item"`. Assert body in response is unchanged.
- `test_html_stripped_on_update` — Create a report, then PUT with `body="<em>updated</em>"`. Assert updated body is `"updated"`.

```bash
.venv/bin/pytest code/backend/tests/test_reports.py -q -k "html_stripped or markdown_preserved"
```

**Manual QA checklist:**

1. Install updated requirements: `pip install -r code/backend/requirements.txt`.
2. Confirm `bleach` is importable: `python -c "import bleach; print(bleach.__version__)"`.
3. Start dev server. Create a report:
   ```bash
   curl -s -X POST .../reports \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"title":"<b>Test</b>","body":"<script>alert(1)</script>Hello","status":"draft"}'
   ```
   Confirm `title` is `"Test"` and `body` is `"Hello"` in the response.
4. Update the report with `body: "**markdown** preserved"`. Confirm no stripping occurs.

---

## Files touched

- [code/backend/requirements.txt](code/backend/requirements.txt)
- [code/backend/app/models/manual_report.py](code/backend/app/models/manual_report.py)

---

## Estimated effort

0.5 dev days

---

## Concurrency & PR strategy

- `Blocking steps:` None. This step is fully independent and may be worked and merged at any time (before or after Step 1, in parallel with Steps 2, 3, 5).
- `Merge Readiness: false` — set to `true` once all 7 acceptance criteria pass.
- Branch: `phase-3.2/step-4-input-sanitization`

---

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| `bleach` + `html5lib` conflict with existing dependencies | Run `pip install bleach>=6.0.0` in the venv and check for conflict warnings before committing `requirements.txt`. |
| Existing stored HTML in reports | This step does not retroactively clean stored data. Acceptable for current dev state. Document as a known gap. |
| `bleach` strips content a user considers valid (e.g., `<br>` line breaks in Markdown) | Acceptable trade-off. The UI uses a plain `<textarea>` today. If a rich text editor is added later, revisit the allowed `tags` list. |

---

## References

- [.github/artifacts/phase3-2/summary/final-report.md](../../summary/final-report.md) — S-12
- [code/backend/app/models/manual_report.py](code/backend/app/models/manual_report.py)
- [bleach documentation](https://bleach.readthedocs.io/)

---

## Author Checklist

- [x] Purpose filled
- [x] Deliverables listed
- [x] `Primary files to change` contains workspace-relative links
- [x] Acceptance Criteria are measurable/testable
- [x] Tests added under `code/backend/tests/`
- [x] Manual QA checklist added
- [x] Backup/atomic-write noted (no schema changes; no migration needed)
