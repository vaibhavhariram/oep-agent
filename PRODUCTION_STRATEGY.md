# Production Strategy

Phase 3. Assume unlimited time, compute, and money. This is what I would actually do, and the order matters more than the list.

---

## 1. I would improve the eval before I improved the agent

The instinct with unlimited resources is to make the system more capable. I would not start there. The bottleneck in this build was never that I couldn't make the agent more complicated. It was that I could not be confident I was measuring correctness the right way.

By the end of the trial the pipeline produced schema-valid output for all ten visible claims, the arithmetic reconciled at both line and case level, and the test suite was green. None of that is the same as being right. It is internal consistency, and internal consistency is exactly what a system produces when it agrees with its own assumptions.

Two things from this build make that concrete.

Seven of my ten golden references are my own adjudication of the policy. If I misread a clause, the system and the test that checks it are wrong in the same direction, and nothing in my tooling would surface it. The three labeled examples Kairos supplied are the only independent ground truth I have, and matching them exactly matters far more to me than matching the seven I wrote myself.

The second is smaller but more instructive. My verification gate has five checks, and on the visible set only one of them had ever failed. That is not evidence the other four work. It is the absence of evidence either way. When I built adversarial cases specifically to break each check, I found that the policy-support check verifies that a cited clause exists in the clause store but does not verify that the cited page number is correct. I only found that because I set out to break my own check rather than to confirm it.

So the first investment is a much larger golden set, built with operator input rather than by me, plus production-trace feedback loops and adversarial cases that stress the failure modes that matter here: false auto-approvals, citation failures, reconciliation conflicts, and unsupported evidence paths.

And the eval itself needs an acceptance bar, because "once I trust the measurement" is not a criterion. Concretely: a clause-coverage matrix showing every policy rule exercised by at least one case; operator inter-rater agreement measured on a shared calibration sample, with a pre-registered threshold (on the order of a Cohen's kappa of at least 0.8) that labels must clear before they are admitted to the golden set; and honesty about statistical power. Ten cases cannot distinguish a real improvement from noise, and I would not treat any system change as validated until the set is large enough that it can. Goldens also get versioned like code: when an operator corrects one, scores before and after the correction are not comparable, and the eval history has to say so.

## 2. Data collection and expert feedback

The single biggest weakness in my evaluation is that I decided what correct looks like. I am not a claims adjuster. I read the policy carefully and wrote down my reasoning clause by clause, but careful reading by a non-expert is not the same as expert judgment, and on a real deployment that gap compounds silently.

I would put claims operators in the loop at the point where the golden set is authored, not at the point where the system is reviewed. My per-claim reasoning documents exist precisely so that this is possible. Each unlabeled golden ships with a written argument citing the clauses behind every line decision, so an adjudicator can disagree with my reasoning rather than just with my number. That also needs a disagreement protocol: when two operators adjudicate the same case differently, the disagreement is itself the signal. It either exposes a policy ambiguity that should become a documented convention, or an error that should become a training example. Both outcomes get captured with rationale, not just resolved.

Beyond the initial set, the higher-value loop is production traces, sampled deliberately rather than randomly. The strata that matter: every escalation, every human override of a system recommendation, cases where the gate score landed near the threshold, high-dollar claims, and any case where two extraction paths disagreed. The failures worth testing are almost never the ones anyone writes down in advance, and uniform sampling mostly re-collects the easy middle. An eval suite that stops growing stops being an eval suite and becomes a regression test.

One constraint shapes all of this: traces contain personal and financial data, and learning across customers is not free. What can pool across deployments is patterns, meaning rule ambiguities, document-format variants, and failure taxonomies. What cannot pool is the data itself. That boundary has to be designed in from the start, not discovered during a customer's security review.

## 3. Techniques: measurement first, then the cheapest learning that works

Only after I trust the eval would I decide what kind of learning is justified, and the ordering runs from cheapest to most expensive.

**First, experience without weight changes.** A large fraction of what this system "learns" in production is not model capability. It is resolved conventions: which line a recovery offsets, whether a duplicate keeps its original classification, how a particular operator wants borderline turnover charges treated. Those belong in a versioned experience store the system retrieves as precedent at decision time. That store is cheap to add, instantly auditable, reversible, and requires no training run. It holds conventions and abstracted case archetypes, never claimant identifiers, which is also what makes deletion requests tractable. Only when precedent retrieval stops closing the gap does anything heavier earn consideration.

**Then specialization, only where the eval demands it.** My current architecture puts a model in exactly one place, reading documents into structured facts, and makes every downstream decision deterministic Python. That split is deliberate: the policy is a deterministic rulebook, so there is no judgment for a model to add, and every dollar is traceable to a rule rather than to a generation. I would keep that boundary. Where specialization earns its cost is the extraction stage, and only once the eval shows a general model is unnecessarily expensive or slow on a well-understood, high-volume subset. Distilling a smaller model into that role is a cost optimization, not a capability improvement.

**If I did train, I would be precise about what a verifiable reward can and cannot verify.** Downstream of extraction, the reward signal is checkable by construction: did the cited clause support the conclusion, do the line amounts reconcile to the case total, was the limit applied after classification. Every one of those is a programmatic check, and RLVR fits exactly there. This is the same reasoning I applied designing an RLVR environment for tau2-bench. But those checks verify consistency, not reading. A model that extracts the wrong figure consistently can satisfy every downstream identity while being wrong at the source. So extraction correctness has to be grounded against independent references: the deterministic parse on structured documents, operator-corrected labels from the review loop, and statistical anomaly detection against historical distributions of amounts and rates, which is also the layer that catches coordinated failures internal reconciliation cannot. Where no independent reference exists, that is a labeling problem, not an RL problem, and pretending otherwise just launders uncertainty through a reward function.

**And the input distribution will not stay still.** Real packets include scans, photographs, and field notes, not clean generated documents. The extraction stage therefore needs vision-capable models and OCR, its eval needs degraded-quality cases, and low-confidence OCR should route a packet away from the automated path entirely rather than feeding garbage forward with high confidence. Policies get amended and formats drift, which means drift detection on extraction-confidence and gate-score distributions, with automatic re-evaluation triggers rather than waiting for a customer to notice.

## 4. Security, privacy, and auditability

The audit trail is not something I would bolt on later, because most of it is already load-bearing in the current design. Every material conclusion carries a clause citation with a page number. Every rule application records its input amount, its adjustment, its output, and an evidence anchor pointing to a specific line on a specific page of a specific document. The system escalates rather than deciding when evidence does not support a determination, and the write-back is a preview that performs no external action.

But a security section without an adversary is a compliance section, so: **claim documents are attacker-controlled input.** Two threat classes matter. A crafted packet can attempt prompt injection against the extraction model, meaning instructions embedded in document text intended to alter extraction. And a fraudulent packet can be tuned to present exactly the evidence pattern that auto-approves. The hardening this implies: document text strictly delimited from instructions in every extraction prompt, extraction models given no tools and no write path, and evasion attempts added to the adversarial suite alongside the accidental failures. The deterministic parser that cross-checks the model contributes here too, within honest limits. An injected instruction can steer a language model but cannot steer a parser, so on born-digital structured documents, agreement between the two raises confidence, and disagreement removes the claim from the auto-approve path and sends it to human review. On degraded or OCR'd inputs, disagreement will usually mean brittle parsing rather than an attacker, so the signal has to be confidence-weighted rather than treated as an alarm. It should act as a tamper indicator that routes to review, not a siren that trains reviewers to ignore it.

Two facts extracted from different documents can also simply conflict. The current design preserves conflicts with provenance from both sides rather than resolving them silently, and a value-changing conflict blocks automation. In production I would add a document-authority hierarchy only where the policy itself defines one; everything else stays mandatory human review, because inventing an authority order the policy does not contain is exactly the kind of silent judgment this architecture exists to avoid.

What I would add on top:

**Policy and rules versioning, together.** Every decision records which policy version produced it, and which version of the deterministic rules code implemented that policy, pinned to it. An audit two years later must reconstruct both the rules in force and the code that executed them. My clause store is currently a single snapshot, which is fine for a trial and wrong for production.

**Reproducibility.** Pinned model versions per deployment, recorded per decision, so any determination can be re-run against the exact model, policy, and rules version that produced it. The schema already separates requested from routed model on every call. That record exists today; production makes it a guarantee.

**Semantic validation beyond types.** Schema validation proves an output is well-formed, not that it is possible. Domain validators sit on top: no negative depreciation, no gap days before possession return, no approved amount above the limit. The arithmetic identities the system already asserts are the start of this layer, not the end of it.

**Full retrieval provenance.** Log the evidence considered, not only the evidence cited. "The system did not see this document" and "the system saw it and discounted it" is the entire question in a dispute.

**Human sign-off as first-class data.** An override is training signal and audit record simultaneously, captured with its reasoning, not just its outcome.

**Baseline controls, stated plainly:** per-customer isolation of data, traces, and model access, with in-environment deployment where required; role-based access separating who can view claims, adjust thresholds, and change policy; encryption in transit and at rest; PII redaction in any trace that leaves the decision boundary for evaluation; retention windows for audit records set by the regulatory regime; and deletion requests satisfiable because the experience store holds abstracted conventions rather than claimant data.

## 5. Path to deployment

None of this ships as a switch-flip, and none of it survives contact with production traffic without ordinary operational reliability underneath: idempotent per-document processing with checkpointed state, so a model API failure mid-claim resumes instead of restarting; exception queues for packets that fail upstream completeness verification, where the manifest gate that already rejects missing, extra, or corrupted files generalizes directly into that routing; dead-letter handling and timeout fallbacks so latency commitments hold under load; and every warning the pipeline generates flowing into the verification gate as an input rather than into a log nobody reads. A signal that cannot change a routing decision is not a control.

The rollout sequence: **shadow mode** first, where the system runs on live claims, decides nothing, and its recommendations are scored against what operators actually did, which simultaneously grows the golden set from the real distribution. Then **assist mode**, where operators see the recommendation, the citations, and the rule trace, and every acceptance or override is recorded with rationale. Then **tiered automation**, where auto-approval is enabled only for the claim segment where accumulated evidence shows the system and operators agree, with everything else still routed to review, and the tier boundary ratcheting outward only as the eval earns it. Autonomy is granted by evidence, not by launch date.

---

## A closing note on what "correct" means here

Seven of the ten visible claims routed to automatic approval under my system. My first reaction was that this seemed high for an exercise about reliability. Looking at it more carefully, the policy gates on unresolved evidence, not on the size of an adjustment. If every line has a supporting record and every deduction is deterministic and fully supported, there is no clause that says to escalate, even when the deductions are large.

I think that is a correct reading of the policy and an incomplete description of what a business would want. One of those claims had $1,944 removed as a duplicate entry. That removal is defensible, auditable, and correct under the rules, and an operator would still almost certainly want to see it before payment went out.

So in production I would add a second lever on top of the policy logic: material-adjustment thresholds that route to human review independently of whether the evidence is resolved. Deliberately, that threshold is a configuration an operator sets, not a value an engineer hardcodes. The policy determines what is supportable. The business determines what is acceptable to automate. Conflating those two is how a system that follows the rules correctly ends up doing something nobody wanted.