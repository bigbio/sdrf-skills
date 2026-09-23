# Reference: reconciling every value against the record (Step 8.5 of sdrf-annotate)

Why the archive's structured fields are not the record, what `sdrf-tools reconcile` reports,
and the four checks worth running by hand.

## Step 8.5: Reconcile every value against the record — REQUIRED

`parse_sdrf` checks that a value is a well-formed term in the right ontology. It cannot
check whether the value is **true of this deposit**. Those are different questions, and the
second one is where annotation actually goes wrong: a batch of 390 files once passed
`parse_sdrf`, a repository review gate and an automated code reviewer while asserting
`organism part = heart` for epicardial adipose tissue, annotating human HeLa QC injections as
mouse heart, writing `Trypsin` for a study that digested nothing, and stamping a patient
diagnosis on wild-type control runs.

Every one of those came from the same habit: **reading the archive's structured fields
(`instruments`, `diseases`, `organismParts`, `organisms`) as if they were the record.** They
are dropdowns the submitter picked at deposition time. The contradicting evidence was
usually in the same JSON — in the title.

Run the reconciler over the finished file before validating it:

```bash
sdrf-tools reconcile <file.sdrf.tsv> --record <project.json> --accession <PXD>
```

It reports a finding whenever the prose, the title or the run names disagree with what was
written, and exits non-zero on a blocker. Treat each finding as a question to answer from the
record, not a value to overwrite blindly.

**What to do with a finding.** Usually the right answer is a sentinel. `not available` is a
result, not a failure: a wrong specific value is worse for reuse than an honest blank,
because a downstream consumer has no way to tell it is wrong.

**The four checks worth running by hand even without the tool:**

1. **Read the title.** It catches most organism-part errors on its own. If the title says
   *epicardial adipose tissue*, *aortic arch* or *carotid plaque*, the sample is not heart —
   whatever the dropdown says.
2. **Read the run names.** They are the submitter's own per-run statement and outrank any
   project-level field. `HCT116_*` and `Hela_*` runs are not the tissue you think you are
   annotating; `_WT_`, `_Ctrl_`, `_SHAM_` and `_Healthy_` runs are not diseased; a `_DDA_`
   run in a DIA deposit is a spectral-library run.
3. **Never broadcast a project-level fact onto every row.** An archive registers one disease
   for a whole project. Most disease studies contain controls, so asserting that diagnosis on
   every row is false for half the file — and if it is also the `factor value`, the one
   contrast the deposit exists for becomes a constant.
4. **Check the file format against the instrument vendor.** A Bruker instrument writes `.d`,
   a Thermo writes `.raw`, a SCIEX writes `.wiff`. An instrument that cannot have produced
   the deposited files is a contradiction that needs no judgement at all.
