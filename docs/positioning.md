# Positioning: Parallax, find what to measure next

Back to [README](../README.md) · Agreed with the teammate in
[Parallax #7](https://github.com/GRAMSINATOR/2026_10_03_hackathon_AI-X-SCIENCE/issues/7).
Every number below comes from the live run (`/v1/results`, Modal cycle 4 Oct 13:50 BST,
journal `37fc0edc…`).

## Who it is for

Battery-electrode process and QC engineers, and the R&D teams behind them. They must decide
whether an incoming supplier batch is the same material as the approved one, using SEM
micrographs.

## Pains we relieve

| Pain today | What Parallax + HackBench does | Evidence from this build |
|---|---|---|
| **Good batches rejected because the microscope changed.** Contrast and focus shifts look like material change. | Material KPIs decide the call; imaging KPIs only raise "acquisition changed" flags. | On the first planted-drift suite, the uncorrected pipeline rejected every imaging-only drift (3/9 correct). Separating the KPI roles gave 5/9 on a held-out suite, with 0 material drifts accepted. The remaining misses are stated: 2 blur false rejects. |
| **A batch call silently hinges on one micrograph.** | Shows which micrograph carries the verdict, and what happens without it. | Batch_3: REJECT at p = 0.017, carried by micrograph M2060 (additive density). Remove M2060 and the batch would pass. |
| **Not knowing what the measurement cannot see.** | Names blind spots explicitly. A second, independent method shows where they bite. | HackBench's tile-level pipeline has no particle-count KPI. It accepts Batch_3, so the two methods disagree, and the console says why. The excess fines sit at the 0.36 µm detection floor. |
| **Literature checks are slow and manual.** | Agentic literature search feeds the opportunity map. An LLM judge checks the literature tool's own output. | 18 verified papers moved 6 gates on Parallax's map: `tomography_3d` → met, `eds` → contested, 4 markers → partial. GXL Paperclip resolved 6/18 of those papers; the judge (`gpt-oss-20b`) found its evidence grounded for 0/26 claims, a measured coverage gap. |
| **"Can I trust the AI's answer?"** | A trust layer: the method is frozen and timestamped before new data, tested against planted known answers and honeypots, and every number traces to a hash-chained journal. | Pre-registered at 10:04:32 BST. A scripted cheating agent tripped 18 honeypots and followed the decoy 9 times; the honest agent tripped 0. |

**One-line pain relief:** stop guessing what to check next. See which signal drives the
call, what your measurement cannot see, and which measurement would settle it, before a bad
batch reaches the line or a good one is scrapped.

## Story arc (video and pitch)

1. **Find what to measure next.** A model can only reason about what it can observe.
2. **Variance:** the Batch_3 reject is carried by one micrograph (M2060). Without it, the batch passes.
3. **Blind spot:** the excess fines sit at the detection floor, and a simpler pipeline cannot see particle counts at all. The two methods disagree, and we show it.
4. **Literature:** agents searched the literature. 18 papers moved the opportunity map; 3-D tomography is "met", and EDS resolution for sub-µm fines is "contested". An LLM judge shows how thin the literature tool's coverage is.
5. **Next measurement:** repeat M2060 under the approved settings at higher magnification; EDS only once its resolution is settled.
6. **Proof and trust:** the verdict, pre-registered and tested on planted drift, with every step on Modal in a hash-chained journal.

## Not claimed

- Time or cost saved in production: no field data.
- HackBench's verdict on the unseen test batch: we had no data for it. Parallax's own call is INVESTIGATE (p = 1.000).
- That Parallax was tested on the planted-drift suite: not yet (Parallax issue #5).
