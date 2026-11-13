# SILAC x neurological disease campaign (2026-11)

Evidence for the SDRFs merged in bigbio/sdrf-annotated-datasets#3091: 8 PRIDE projects, 13 SDRFs.

- `silac_neuro.md`, `silac_neurological.md`: the screening criteria. The second widens rule 2 from
  neurodegenerative to neurological diseases; it was adopted mid-campaign.
- `screen_*.tsv`: one screening decision per candidate, per criteria file.
- `<PXD>/`: per accession, the producer report, the evidence manifest(s), the validation log and every
  independent review report (`review-*.review.json`, PASS and FAIL rounds).

These are per-round records. A producer report or review report describes the state when it was
written: earlier rounds name artifact paths that were later renamed (PXD001942, PXD010671) and scratch
paths of the annotation environment. Each included dataset's report opens with a **Final outcome**
block naming the committed file, its sha256 and the review report that approved that exact hash; that
block is authoritative. Review reports are left as the reviewers wrote them.
