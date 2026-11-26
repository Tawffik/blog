# Tests that pass when the server says no: a zero-budget contract CI for a knowledge platform that must refuse unsourced claims

*Published November 26, 2026 · Labels: `PERSONAL_PROJECT`, `SECURITY_RESEARCH` · Arabic summary at the end (ملخص عربي في الآخر).*

Most test suites answer one question: does the happy path work. This article is about the opposite question, and why it matters more for a security knowledge platform: does the system actually refuse what it promises to refuse, on every commit, for zero dollars.

The subject is the contract CI of my knowledge-platform project (private repository, commit `10ae799`, November 26, 2026). The platform stores security knowledge, project metrics and review decisions. Its governing rule, written into the API contract itself, is that every claim on screen carries replayable evidence: a knowledge entry must name a source and a check date, a metric run must name the command that produced it, a review decision must name its reason. A rule like that is a promise. A promise you never attack is marketing, so the CI attacks it three different ways, in about five seconds, with no external services.

The repository is private, so instead of links you get the load-bearing code verbatim, and an independent replay I ran on a clean checkout today. Evidence tags: **[tested]** means I executed it myself on November 26, 2026, **[documented]** means it comes from a source file at the stated commit.

## Results at a glance

| | |
|---|---|
| Subject | contract CI of the knowledge-platform repo (private), commit `10ae799` [documented: git log, November 26, 2026] |
| Shape | one command, `./ci_offline.sh`: lint, then 17 offline tests, then 8 live negative tests against an ephemeral server [documented: `contract/ci_offline.sh`] |
| Governing rule | no knowledge entry without `source_url` + `checked_at`, no metric run without `run_command`, no review without `reason`, verification label restricted to `tested` / `documented` / `untested` [documented: `contract/openapi.yaml`] |
| Independent replay | cloned fresh, ran the script: `17 passed` offline, `8 passed` live negative, `CI RESULT: PASS`, 5.3 s wall on a free sandbox **[tested, November 26, 2026]** |
| External dependencies | none by construction: random localhost port, throwaway SQLite deleted after the run, no accounts, no API keys [documented: script header; consistent with my run output] |
| Cost | $0 |
| What it does not prove | platform correctness beyond the contract surface; see the limits section |


## The contract is the product

The API surface is deliberately small: five paths, `/projects`, `/projects/{slug}`, `/knowledge`, `/ledger`, `/reviews` [documented: `contract/openapi.yaml`, 199 lines]. The contract's own description states the governing principle (originally written in Arabic): every claim on screen has replayable evidence (an Evidence plus a MetricRun), and every knowledge entry carries a verification label, a source and a check date.

That principle becomes three concrete refusal requirements, and each one has a test that fails if the server stops refusing:

```python
def test_knowledge_entry_without_source_rejected():
    """إدخال معرفة بلا source_url/checked_at يُرفض — الصدق هيكلي."""
    r = CLIENT.post("/knowledge", json={
        "title": "أداة X", "kind": "tool-note", "verification": "tested"})
    assert r.status_code in (400, 422)

def test_knowledge_entry_invalid_verification_label_rejected():
    """تصنيف تحقق خارج (tested/documented/untested) يُرفض."""
    r = CLIENT.post("/knowledge", json={
        "title": "أداة Y", "kind": "tool-note", "verification": "probably-free",
        "source_url": "https://example.com", "checked_at": "2026-11-25"})
    assert r.status_code in (400, 422)

def test_ledger_entry_without_run_command_rejected():
    """تشغيلة بلا أمر تشغيل تُرفض — لا قابلية تكرار بلا أمر."""
    r = CLIENT.post("/ledger", json={
        "project_slug": "vulnradar", "action": "scan", "result": "pass",
        "ran_at": "2026-11-25T21:00:00Z"})
    assert r.status_code in (400, 422)
```

[documented: `contract/test_contract_negative.py`, verbatim, Arabic docstrings kept]

Note the polarity. These tests **pass only when the server rejects**. A conventional suite checks that valid input works, and a bug that accepts garbage stays green. Here, the day the server starts accepting an unsourced knowledge entry, CI goes red. For a platform whose entire value proposition is "no claim without evidence", the rejection path is the critical path.


## Three layers, because each one can lie in a different way

**Layer 1, schema offline (9 tests).** Validates the schemas inside `openapi.yaml` itself, with no server at all: valid payloads validate, corrupt payloads fail validation [documented: `contract/test_schema_offline.py`]. This answers a subtle question: is the 422 you expect actually *described* in the contract, or just intended? A refusal that exists only in the server code is one refactor away from disappearing. When the schema itself rejects `"verification": "probably-free"`, the contract documents the refusal.

**Layer 2, contract parity (8 tests).** Boots the reference implementation in-process with FastAPI's `TestClient`, pulls its generated `/openapi.json`, and diffs it against the hand-written contract: every documented route must be implemented, no undocumented routes may exist, and `ProjectDetail` must carry `evidence` and `metrics` [documented: `contract/test_contract_parity.py`]. This kills the two classic drift failures: the spec that describes endpoints nobody built, and the server that grew endpoints nobody documented. Both directions are tested, which is the part most contract setups skip.

**Layer 3, live negative (8 tests).** The only layer that needs a real server, run against an ephemeral uvicorn on a random port. Six refusal cases (the three above, plus review without reason, invalid review decision, slug pattern enforcement) and two shape checks (list endpoint, exposed API docs). Its skip discipline is stated in the file header: without a server, every test skips with a declared reason, because a missing server is a measured runtime state, not an expected result. A skip that reads as a pass is how suites lie.

```
17 passed  (offline: schema + parity)
8 passed   (live negative)
CI RESULT: PASS (lint see above, 17 offline + 8 live negative)
```

**[tested]** Output of my independent replay today, on a clean checkout at `10ae799`, in a fresh sandbox: ruff clean, 17 offline passed, server came up on a random port, 8 live negative passed, 5.3 seconds wall clock total.


## The zero-budget part is the interesting engineering

Everything runs on localhost, once, and cleans up after itself. The harness core [documented: `contract/ci_offline.sh`, abridged]:

```bash
PORT=$(python3 - <<'PY'
import socket
s = socket.socket(); s.bind(("127.0.0.1", 0))
print(s.getsockname()[1]); s.close()
PY
)
BASE_URL="http://127.0.0.1:${PORT}"
DB_PATH="/tmp/platform-ref-ci.db"
rm -f "$DB_PATH" /tmp/platform-ref.db
...
( cd reference && nohup python3 -m uvicorn app:app --host 127.0.0.1 --port "${PORT}" ... & )
# wait up to 30s for /openapi.json, then:
python3 -m pytest test_contract_negative.py -q || FAIL=1
kill "$(cat /tmp/kp-ci-uvicorn.pid)" 2>/dev/null
rm -f /tmp/kp-ci-uvicorn.pid "$DB_PATH" /tmp/platform-ref.db
```

Three decisions worth stealing:

1. **Random port from the OS, not a hardcoded one.** The script asks the kernel for a free port instead of assuming `:8000` is free. The suite works on a machine where something else is already running, which is exactly the machine a contributor has.
2. **A throwaway database, deleted on exit.** `platform-ref-ci.db` is created fresh and removed after the run. No seed state leaks between runs, so a green run today means the same thing as a green run last week. Test suites that accumulate state are quietly comparing against history, not against the contract.
3. **Declared skips, never silent passes.** If ruff is missing the script prints `SKIP lint: ruff not installed (declared skip, not a pass)` and continues. If the server never comes up, the script fails loudly with the uvicorn log instead of letting the negative suite skip green. The difference between "we did not check" and "we checked and it passed" is preserved in the output, which is the same evidence discipline this blog applies to security claims, enforced by a shell script.

The reference implementation itself is 273 lines of FastAPI plus raw SQLite [documented: `contract/reference/app.py`]: no accounts, no ORM, no hosted anything. The whole gate, contract plus implementation plus 25 tests, runs on any laptop with Python 3.11 in about five seconds. When your budget is zero, "the CI needs a staging environment" is not a constraint, it is a design error.


## Limits, stated before someone else states them

- **25 tests over 5 paths is evidence about the contract surface, not proof the platform is correct.** It says nothing about performance, concurrency, injection beyond the validated fields, or any endpoint outside the contract. A lesson I keep pinned in the portfolio's notes applies verbatim: a passing test count is evidence about behavior, not a completion claim, and "17 offline + 8 live" only means something with its scope attached [documented: portfolio `notes/lessons-learned.md`].
- **The repo is private, so the replay is not open to you.** The method is fully visible above and the run is re-executed by me with date and commit, but that is reported evidence, not a link you can click. Publishing the repo is a separate decision I have not made yet.
- **The negative suite pins status codes (400/422), not error quality.** A server that rejects with an unhelpful message still passes. Error-contract testing is a known gap.
- **The reference server is a reference, not production.** It gates the first implementation version against the contract (its stated role as an acceptance gate: 8/8 must pass), and SQLite plus uvicorn is a deliberately minimal stand-in.
- **My replay ran on a machine with network access;** the script opened no external connections by construction (localhost only, no credentials, no remote fetches in the run output), but I did not rerun it inside a network namespace. The honest claim is "no external services by construction, observed none in my run", not "proven offline".


## ملخص عربي

الموضوع: الـ CI بتاع منصة المعرفة (ريبو خاص، كوميت `10ae799`). القاعدة الحاكمة في العقد: كل ادعاء على الشاشة ليه دليل قابل للتكرار، يعني ممنوع إدخال معرفة من غير مصدر وتاريخ فحص، وممنوع تشغيلة من غير أمر تشغيل، وممنوع قرار مراجعة من غير سبب. القاعدة من غير اختبار يهاجمها تبقى كلام، فالـ CI بيهاجمها بثلاث طبقات: سكيما أوفلاين (العقد نفسه بيرفض الحمولات الفاسدة)، تطابق (الخادم المرجعي مطابق للعقد في الاتجاهين، مفيش مسارات زيادة ولا ناقصة)، وسالب حي (٨ اختبارات بتنجح بس لما الخادم يرفض فعلًا بـ 400/422). شغّلت السكريبت بنفسي على نسخة نضيفة النهارده: lint نضيف، 17 أوفلاين نجحوا، 8 سالب حي نجحوا، النتيجة PASS في 5.3 ثانية، وبلا أي خدمة خارجية: بورت عشوائي من النظام وقاعدة SQLite مؤقتة بتتمسح بعد الجولة، يعني التكلفة صفر فعلًا. الحدود بصراحة: دي شهادة على سطح العقد مش إثبات إن المنصة سليمة كليًا، والريبو خاص فالتكرار متاحش للقارئ لسه، وقرار النشر لسه ماتخدش.
