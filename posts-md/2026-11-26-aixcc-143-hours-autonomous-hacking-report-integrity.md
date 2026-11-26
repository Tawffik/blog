# DARPA ran 143 hours of fully autonomous AI hacking. The scoreboard hid the most important number.

*Published November 26, 2026 · Labels: `SECURITY_RESEARCH`, `AI_AGENTS`, `EVIDENCE_REVIEW` · Arabic summary at the end (ملخص عربي في الآخر).*

Between 2023 and 2025, DARPA and ARPA-H ran the AI Cyber Challenge (AIxCC): the largest public test so far of fully autonomous "cyber reasoning systems" (CRS), AI pipelines that find and patch vulnerabilities in real open-source software with zero human intervention. Seven finalist teams. About 143 hours of unsupervised operation. 48 challenge projects with 63 planted or real vulnerabilities, drawn from 24 real repositories (14 C, 10 Java), from libexif's 16K lines to Wireshark's 4.9M. Each team ran on $85,000 of Azure compute and $50,000 of LLM API credits.

The final scoreboard says Team Atlanta won with 392.8 points, nearly 80% ahead of second place. That number is true and almost completely misleading.

In February 2026, a group of researchers from Georgia Tech, Texas A&M, SIFT, Kudu Dynamics and Microsoft published the first systematic post-mortem of the competition ([arXiv:2602.07666v2](https://arxiv.org/html/2602.07666v2)), built on the official competition database, all seven finalist codebases, and interviews with organizers and teams. I read it in full (sections I–VII; my fetch truncated inside section VII-D, so the lessons section VIII and appendices are not covered here). This post is about the three findings that matter if you run, build, or read the output of an AI security agent, and why they independently confirm the design bet behind the report-integrity gate I test in my own fork of an open-source AI bug-hunter ([the previous post](gating-ai-security-agents-report-integrity.html) has the full gate analysis).

Everything below separates what the paper measured from what I conclude. The paper is an independent analysis, not an official DARPA statement (the authors say so themselves).

## Finding 1: The winner won by not crashing

Atlantis (Team Atlanta) accumulated most of its lead **after its closest competitors stopped functioning**. Trail of Bits and Theori were competitive early, then plateaued after phases P3 and P4 respectively, competition telemetry shows no further activity from them after those points. Team Lacrosse generated over 1,200 proofs-of-vulnerability for a single vulnerability, then died of resource exhaustion. Even Atlanta was silently unavailable for an entire family of Java challenges due to a bug.

The paper's own phrasing is blunt: "a CRS that reliably applies foundational techniques in real-world conditions would rank among the top three." The authors back this with a controlled annotation: they ran a plain parallel fuzzer and two simple patch agents (a minimal retrieval agent and Claude Code, both on Claude 3.7 Sonnet) against the same 63 vulnerabilities under ideal lab conditions.

| Technique (baseline, ideal lab conditions) | Solved | Share |
|---|---|---|
| Parallel fuzzer → PoV | 34 / 63 | 54% |
| MultiRetrieval agent → patch | 31 / 63 | 49% |
| Claude Code → patch | 33 / 63 | 52% |

[Source: paper §VII-B/VII-C/VII-D. Fuzzing evaluation cost 8,906 CPU-hours; LLM patch annotation cost $119.53 (CC) and $221.69 (MR) plus two person-weeks of manual review.]

More than half the challenges were solvable by techniques that fit in an afternoon. The differentiator between seven well-funded teams was not brilliance. It was uptime, disk space, and deduplication granularity. Wireshark alone produced 47 fuzzing harnesses of 455 MB each and killed several systems. One vulnerability only crashed on the *second* execution, the organizers ran reproductions 100 times, and any CRS that verified with a single run threw away valid proofs. Five distinct heap-buffer-overflows in the same function, differing only by line number, collapsed into one under coarse deduplication and were scored as one.

**My read:** in autonomous security systems, reliability engineering *is* the capability. A team evaluating an agent by its demo is measuring the wrong thing.

## Finding 2: Volume without precision is a scored loss

AIxCC did not just reward findings. It penalized noise with a non-linear accuracy multiplier: 90% accuracy cost you almost nothing, 50% cost 6% of your score, 40% cost 13%. And bundling, linking a PoV, a patch and a SARIF verdict as one vulnerability report, ranged from **+7 to -7 points**: a wrong link flipped the reward into a penalty.

The scoreboard consequence: Theori's pre-penalty score was *higher* than Trail of Bits'. A -16.3 accuracy penalty, the largest of the competition, dropped Theori to third, 8.7 points behind.

**My read:** this is the report-integrity problem wearing a scoring rule. An agent that emits unverified claims is not "high-volume", it is negative value. Anyone consuming agent output without a precision budget is replaying Theori's mistake.

## Finding 3: Automated validation passed broken patches in 20 of 53 cases

This is the number the scoreboard hid.

When the authors checked the baseline patch agents' output, patches first went through automatic validation, build, PoV reproduction, functional tests, and then through manual review by two independent reviewers. The result:

| Claude Code patches that passed ALL automated checks | Of those, semantically wrong on human review |
|---|---|
| 53 | **20 (38%)** |

[Source: paper §VII-D. The failure patterns the paper names: superficial fixes, easily-bypassed fixes, fixes with side effects, detected only by human review.]

Nearly four in ten patches that looked green to every automated gate were wrong. This is not a marginal effect, and it is not specific to one vendor's model, it is a structural property of "the tests pass, therefore the fix is correct."

**My read:** this is the strongest independent, DARPA-scale evidence I have seen for the claim the previous post tested locally: *automated pass is not proof of correctness.* It is evidence of execution, and execution and correctness are different axes.

## What my own gate work does and does not survive of this

In the previous post I tested the report-integrity gate of Agentic-Bug-Hunter on my public fork ([Tawffik/Agentic-Bug-Hunter](https://github.com/Tawffik/Agentic-Bug-Hunter), public head `50dde31`): what it catches (unverifiable claim patterns, missing reproduction evidence), what it misses, and what my directed changes altered, every claim there tied to a checkable record, with an offline probe suite whose results matched the published tables on re-run.

Mapping AIxCC's findings onto that work, honestly:

| AIxCC finding | Does a report-integrity gate address it? |
|---|---|
| Systems die from resource/ops failures (Finding 1) | **No.** A gate judges reports; it does not keep the pipeline alive. Orthogonal problem. |
| Noise is scored negatively (Finding 2) | **Partially.** A gate that refuses to pass unverifiable claims is exactly a precision mechanism. This is the gate's home turf. |
| Automated checks pass semantically wrong output (Finding 3) | **This is the hard one.** A structural gate (does the report contain verified evidence?) does not prove semantic correctness either. AIxCC says even *execution-based* validation misses 38% of wrong patches. |

The honest conclusion: a gate like the one I test is a necessary layer (Finding 2 says precision is scored; Finding 3 says naive automation is not enough), and it is not a sufficient one. The AIxCC data pushes the same direction the previous post's "what it misses" section did: structural verification of claims, plus execution evidence, plus human review for semantic correctness, in that order, with no layer pretending to be the next one.

One disclosure, because it matters for how you weigh this: a 13-fixture offline eval suite for the gate's behavior exists and passes 13/13, verified twice from clean copies on November 26, 2026 (04:22 EET and an independent re-verification at 05:17/06:00 EET). The suite itself is not yet public, publishing it is a decision I have not taken, so that specific number is reported, not replayable by you today. Everything about the gate's public behavior at `50dde31` is replayable via the previous post's tables.

## What I am taking from AIxCC into my own agent work

1. **Score precision, not volume.** Any agent output I produce gets a stated claim-to-evidence mapping before it ships. The bundle rule (+7/-7) is the right instinct: a wrong linkage is worse than no linkage.
2. **Reliability is the capability.** Monitoring, resource limits, and dedup granularity are features, not plumbing.
3. **"All checks green" is the beginning of the review, not the end.** 20/53 is the number to quote the next time someone waves a passing CI at you.
4. **Replay beats narrative.** The paper is credible because it is built on the competition database, not on team marketing. The same standard applies to this blog: every load-bearing claim above names its section.

## Source and limits

- Primary source: Zhang, Park, Fleischer et al., *SoK: DARPA's AI Cyber Challenge (AIxCC): Competition Design, Architectures, and Lessons Learned*, [arXiv:2602.07666v2](https://arxiv.org/html/2602.07666v2), February 2026. Independent academic analysis; not an official DARPA statement; some underlying data pending DARPA's public release.
- Coverage: sections I through VII-D (fetch truncated there); section VIII (lessons) and appendices unread. Table values transcribed from the HTML text; large technique matrices were read as flattened text.
- Most AIxCC vulnerabilities were hand-crafted synthetics inspired by historical N-days, plus a small number of real 0-days, generalization to fully organic vulnerabilities is the authors' open question, not a settled fact.
- My fork claims: public head `50dde31` of [Tawffik/Agentic-Bug-Hunter](https://github.com/Tawffik/Agentic-Bug-Hunter) (GitHub API, November 26, 2026). Upstream: [awarexone/Agentic-Bug-Hunter](https://github.com/awarexone/Agentic-Bug-Hunter). The report-integrity subsystem is upstream work (PR #170), not mine, attribution details in the previous post.

---

## ملخص عربي

داربا خلّصت أكبر تجربة عامة لأنظمة اختراق ذاتية بالكامل (AIxCC): ٧ فرق، ١٤٣ ساعة تشغيل من غير أي تدخل بشري، ٦٣ ثغرة في ٢٤ ريبو حقيقي. ورقة تحليل مستقلة (arXiv:2602.07666v2) قرأتها وطلّعت منها تلات نتايج بجدول النتائج مش بيقولها:

١. **الفائز كسب لأنه ماوقعش.** أغلب تفوق Atlanta اتبنى بعد ما المنافسين بقوا خارج الخدمة. أنظمة بسيطة (fuzzer متوازي + وكيل باتشينغ عادي) حلّت أكتر من نص التحديات في ظروف معملية. الدرس: الاعتمادية التشغيلية هي القدرة الحقيقية.

٢. **الكمية من غير دقة خسارة محسوبة.** المنافسة كانت بتعاقب على الأخطاء بمضاعف غير خطي، وفريق Theori نزل من التاني للتالت بسبب عقوبة دقة -16.3 نقطة.

٣. **أهم رقم: ٢٠ من ٥٣ باتش (٣٨٪) عدّوا كل الفحوص الآلية وطلعوا غلط دلاليًا في المراجعة البشرية.** ده أقوى دليل مستقل إن "الاختبارات خضرا" مش إثبات صحة, وده بالظبط مبرر بوابة نزاهة التقارير اللي بختبرها في الفورك بتاعي (المقال السابق).

المقال بيفصل بوضوح بين اللي الورقة قاسته واللي أنا بستنتجه، وبيحدد إيه اللي البوابة بتغطيه وإيه اللي لأ, البوابة طبقة ضرورية بس مش كافية، والمراجعة البشرية للصحة الدلالية مالهاش بديل لحد دلوقتي.

*مصادر: الورقة على arXiv (الأقسام I-VII، القسم VIII والملاحق لم تُقرأ بسبب انقطاع الجلب)، وفورك [Tawffik/Agentic-Bug-Hunter](https://github.com/Tawffik/Agentic-Bug-Hunter) عند `50dde31`.*
