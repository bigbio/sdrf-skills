"""Tests for tools.record_reconcile.

Every case here is a defect observed in a real annotated batch, where the written value was a
valid ontology term that passed `parse_sdrf` and a repository review gate while contradicting
the deposit it described. The accession in each docstring is the deposit the case came from.
"""

from __future__ import annotations

from tools.record_reconcile import (
    BLOCKER,
    MAJOR,
    acquisition_from_run_name,
    check_acquisition,
    check_cleavage_agent,
    check_disease,
    check_instrument,
    check_labelled,
    check_organism,
    check_organism_part,
    proteases_in_record,
    reconcile,
    sentences,
)


def rec(**kw) -> dict:
    base = {"title": "", "projectDescription": "", "sampleProcessingProtocol": "",
            "dataProcessingProtocol": "", "quantificationMethods": []}
    base.update(kw)
    return base


class TestSentences:
    def test_does_not_split_on_decimals(self):
        assert len(sentences("Peptides were 1.5 ug. Next step.")) == 2

    def test_does_not_split_on_a_temperature(self):
        """A trailing '37 °C.' keeps the following clause in the same sentence.

        That merges two sentences, which is the safe direction: a merged sentence carrying
        both a digest cue and a role-exclusion word is rejected, so the check fails closed.
        """
        assert len(sentences("Digested at 37 °C. Peptides were desalted.")) == 1

    def test_does_not_split_on_abbreviations(self):
        assert len(sentences("Enzymes, e.g. trypsin, were used. Then LC-MS.")) == 2


class TestProteaseRole:
    """The matched word must be playing the part of a digest reagent."""

    def test_tryptic_is_trypsin(self):
        """PXD044170: '\\btrypsin' does not match 'tryptic', so the real enzyme was lost."""
        r = rec(sampleProcessingProtocol="Tryptic digestion was performed using the SP3 protocol.")
        assert proteases_in_record(r) == ["Trypsin"]

    def test_chymotrypsin_like_activity_is_not_a_digest(self):
        """PXD044170: 'chymotrypsin-like activity' is a proteasome assay readout."""
        r = rec(projectDescription="Investigation of the UPS showed a higher chymotrypsin-like "
                                   "activity after TAC.",
                sampleProcessingProtocol="Tryptic digestion was performed for 50 ug protein.")
        assert proteases_in_record(r) == ["Trypsin"]

    def test_trypsin_as_the_analyte_is_not_a_digest(self):
        """PXD026332: a plasma peptidomics study that digests nothing."""
        r = rec(projectDescription=(
            "We investigated in plasma of heart failure patients the presence of pancreatic "
            "trypsin, a major enzyme responsible for digestion. The plasma trypsin levels are "
            "elevated. The peptides exhibit cleavage sites by trypsin."))
        assert proteases_in_record(r) == []

    def test_sequential_digest_reports_both_enzymes(self):
        """PXD027772: the second enzyme sits far from the single 'digested with'."""
        r = rec(sampleProcessingProtocol=(
            "30 ug of protein was digested with Lys-C (FUJIFILM Wako) for 4 h and subsequently "
            "with modified porcine trypsin for 16 h at 37 °C."))
        assert set(proteases_in_record(r)) == {"Trypsin", "Lys-C"}

    def test_search_setting_still_counts(self):
        """The submitter stating the search enzyme is still stating the digest."""
        r = rec(dataProcessingProtocol="The enzyme specificity was trypsin.")
        assert proteases_in_record(r) == ["Trypsin"]


class TestCleavageAgent:
    def test_fabricated_enzyme_is_a_blocker(self):
        r = rec(sampleProcessingProtocol="Tryptic digestion was performed for 50 ug protein.")
        f = check_cleavage_agent(r, ["NT=Chymotrypsin;AC=MS:1001306"])
        codes = {x.code for x in f}
        # Both halves of the real defect are reported: a fabricated enzyme, and the actual
        # enzyme missing.
        assert "cleavage_agent_contradicted" in codes
        assert "cleavage_agent_incomplete" in codes
        assert BLOCKER in {x.severity for x in f}

    def test_unsupported_enzyme_when_record_names_none(self):
        f = check_cleavage_agent(rec(), ["NT=Trypsin;AC=MS:1001251"])
        assert f and f[0].code == "cleavage_agent_unsupported"

    def test_co_digest_reduced_to_one_enzyme(self):
        r = rec(sampleProcessingProtocol=(
            "Protein was digested with Lys-C for 4 h and subsequently with trypsin overnight."))
        f = check_cleavage_agent(r, ["NT=Trypsin;AC=MS:1001251"])
        assert [x.code for x in f] == ["cleavage_agent_incomplete"]
        assert f[0].severity == MAJOR

    def test_complete_co_digest_is_clean(self):
        r = rec(sampleProcessingProtocol=(
            "Protein was digested with Lys-C for 4 h and subsequently with trypsin overnight."))
        assert check_cleavage_agent(
            r, ["NT=Trypsin;AC=MS:1001251", "NT=Lys-C;AC=MS:1001309"]) == []


class TestOrganism:
    def test_declared_species_absent_from_the_record(self):
        """PXD041192: PRIDE registers Homo sapiens for a murine study."""
        r = rec(title="Therapeutic remodelling of murine heart",
                projectDescription="Mice were given a coronary artery occlusion.")
        f = check_organism(r, "Homo sapiens")
        assert f and f.severity == BLOCKER

    def test_passing_mention_is_not_a_contradiction(self):
        """A human search database or ortholog must not flag a mouse deposit."""
        r = rec(title="Mouse heart proteome",
                dataProcessingProtocol="Searched against the human UniProt database.")
        assert check_organism(r, "Mus musculus") is None

    def test_agreement_is_clean(self):
        assert check_organism(rec(title="Mouse heart"), "Mus musculus") is None


class TestOrganismPart:
    def test_title_names_adipose_not_heart(self):
        """PXD028158: PRIDE's dropdown said Heart; the title says epicardial adipose tissue."""
        r = rec(title="Proteomics of epicardial adipose tissue in heart failure patients")
        f = check_organism_part(r, "heart")
        assert any(x.code == "organism_part_contradicted" and x.severity == BLOCKER for x in f)

    def test_title_names_aortic_arches(self):
        """PXD020406: 'aortic arches' -- note plural, which a \\barch\\b pattern misses."""
        r = rec(title="Wild-type and O/E uPA in mouse aortic arches")
        assert any(x.code == "organism_part_contradicted" for x in check_organism_part(r, "heart"))

    def test_run_names_name_a_cell_line(self):
        """PXD045956: 22 of 66 runs are HCT116, annotated as mouse heart."""
        runs = ["20220608_HCT116_DDA_1", "20220608_HCT116_DDA_2", "mouse_heart_1"]
        f = check_organism_part(rec(), "heart", runs)
        assert any(x.code == "run_names_name_a_cell_line" for x in f)

    def test_run_names_name_another_organ(self):
        """PXD051406: 22 of 42 runs are named Aorta-*."""
        f = check_organism_part(rec(), "heart", ["Aorta-Ctr_01", "Aorta-Ctr_02", "heart_1"])
        assert any(x.code == "run_names_name_another_organ" for x in f)

    def test_cultured_material_has_no_anatomical_source(self):
        r = rec(title="Proteome of hiPSC-derived cardiomyocytes")
        assert any(x.code == "organism_part_from_cultured_material"
                   for x in check_organism_part(r, "heart"))

    def test_genuine_tissue_is_clean(self):
        r = rec(title="Left ventricular tissue from eight individuals")
        assert check_organism_part(r, "heart", ["LV_1", "LV_2"]) == []

    def test_sentinel_is_never_flagged(self):
        assert check_organism_part(rec(title="epicardial adipose"), "not available") == []


class TestInstrument:
    def test_vendor_cannot_write_the_format(self):
        """PXD076291: a Thermo Q Exactive HF declared for Bruker .d files."""
        f = check_instrument(rec(), "Q Exactive HF", ["a.d.zip", "b.d.zip"])
        assert any(x.code == "instrument_cannot_write_these_files" and x.severity == BLOCKER
                   for x in f)

    def test_bruker_cannot_write_thermo_raw(self):
        """PXD029649: timsTOF Pro declared over Thermo .raw files."""
        f = check_instrument(rec(), "timsTOF Pro", ["MD131PRM1_1.raw"])
        assert any(x.code == "instrument_cannot_write_these_files" for x in f)

    def test_neutral_formats_do_not_trigger(self):
        assert not [x for x in check_instrument(rec(), "Q Exactive HF", ["a.mzML"])
                    if x.code == "instrument_cannot_write_these_files"]

    def test_matching_vendor_is_clean(self):
        assert check_instrument(rec(), "Q Exactive HF", ["a.raw"]) == []

    def test_protocol_names_a_more_specific_model(self):
        r = rec(sampleProcessingProtocol="Data were recorded on a Q Exactive HF-X.")
        f = check_instrument(r, "Q Exactive", ["a.raw"])
        assert any(x.code == "instrument_contradicted" for x in f)


class TestDisease:
    def test_disease_on_control_named_runs(self):
        """PXD027772: 20 of 44 runs are SKM_WT_*, all asserting Duchenne muscular dystrophy."""
        runs = ["SKM_DMD_1", "SKM_DMD_2", "SKM_WT_3", "SKM_WT_4"]
        f = check_disease(rec(), "duchenne muscular dystrophy", runs)
        assert any(x.code == "disease_on_control_runs" and x.severity == BLOCKER for x in f)

    def test_control_arm_named_only_in_the_record(self):
        """PXD055505: runs use a bare C_ prefix, but the record says 'sham group'."""
        r = rec(projectDescription="Mice were divided into a sham group (n = 10) and an "
                                   "ischemic group (n = 10).")
        f = check_disease(r, "cerebrovascular disease", ["C_Brain_1", "I_Brain_1"])
        assert any(x.code == "disease_with_control_arm_in_record" for x in f)

    def test_value_that_is_not_a_disease_term(self):
        """PXD046496: 'inflammation' resolves only to a symptom/phenotype ontology."""
        f = check_disease(rec(), "inflammation", ["r1"])
        assert any(x.code == "not_a_disease_term" for x in f)

    def test_generic_registry_bucket(self):
        f = check_disease(rec(), "cardiovascular system disease", ["r1"])
        assert any(x.code == "generic_disease_bucket" for x in f)

    def test_sentinel_and_normal_are_clean(self):
        assert check_disease(rec(), "not available", ["ctrl_1"]) == []
        assert check_disease(rec(), "normal", ["ctrl_1"]) == []

    def test_specific_diagnosis_without_controls_is_clean(self):
        assert check_disease(rec(), "dilated cardiomyopathy", ["P1", "P2"]) == []


class TestAcquisition:
    def test_dda_library_runs_in_a_dia_deposit(self):
        """PXD050447: 200 of 799 runs are _DDALib_, all annotated DIA."""
        runs = ["s_DIA_1", "s_DIA_2", "pool_DDALib_F01"]
        declared = ["Data-independent acquisition"] * 3
        f = check_acquisition(declared, runs)
        assert f and f[0].severity == BLOCKER

    def test_sciex_ida_is_dda(self):
        assert acquisition_from_run_name("2018_pool_IDA_6") == "Data-dependent acquisition"

    def test_prm_with_a_trailing_digit(self):
        """PXD031424: 188 of 248 runs are *PRM1..N, annotated DDA."""
        assert acquisition_from_run_name("AMPK-Control-Try-PRM1") == "Parallel reaction monitoring"

    def test_parameter_spelling_is_understood(self):
        f = check_acquisition(["NT=Data-independent acquisition;AC=PRIDE:0000450"],
                              ["sample_DDA_1"])
        assert f and f[0].code == "acquisition_contradicted_by_run_name"

    def test_agreement_is_clean(self):
        assert check_acquisition(["Data-independent acquisition"] * 2, ["a_DIA_1", "b_SWATH_2"]) == []

    def test_uninformative_run_names_are_clean(self):
        assert check_acquisition(["Data-independent acquisition"] * 2, ["1.raw", "2.raw"]) == []


class TestLabelled:
    def test_quantification_method_field_is_decisive(self):
        """PXD016095: PRIDE registers 'MS1 based isotope labeling'."""
        r = rec(quantificationMethods=["MS1 based isotope labeling"])
        assert check_labelled(r, "NT=label free sample;AC=MS:1002038") is not None

    def test_reductive_demethylation_spelling(self):
        """PXD016095: the submitter wrote 'demethylation', not 'dimethylation'."""
        r = rec(sampleProcessingProtocol=(
            "Chemical labeling by reductive demethylation was performed, labeling 'light' for "
            "wt and 'heavy' for the knockout."))
        assert check_labelled(r, "NT=label free sample;AC=MS:1002038") is not None

    def test_tmt_plex(self):
        r = rec(sampleProcessingProtocol="Analysed with a TMT2-plex method.")
        assert check_labelled(r, "NT=label free sample;AC=MS:1002038") is not None

    def test_label_free_deposit_is_clean(self):
        r = rec(sampleProcessingProtocol="Label-free quantification was performed.")
        assert check_labelled(r, "NT=label free sample;AC=MS:1002038") is None

    def test_declared_labelled_channel_is_not_flagged(self):
        r = rec(quantificationMethods=["TMT"])
        assert check_labelled(r, "NT=TMT126;AC=MS:1002623") is None


class TestReconcileEntryPoint:
    def _rows(self, n=2, **over):
        base = {
            "source name": "PXD1-Sample-1",
            "characteristics[organism]": "Mus musculus",
            "characteristics[organism part]": "heart",
            "characteristics[disease]": "not available",
            "assay name": "run1",
            "comment[instrument]": "NT=Q Exactive HF;AC=MS:1002523",
            "comment[cleavage agent details]": "NT=Trypsin;AC=MS:1001251",
            "comment[proteomics data acquisition method]": "Data-dependent acquisition",
            "comment[label]": "NT=label free sample;AC=MS:1002038",
            "comment[data file]": "run1.raw",
        }
        base.update(over)
        return [dict(base, **{"assay name": f"run{i}", "comment[data file]": f"run{i}.raw"})
                for i in range(1, n + 1)]

    def test_clean_annotation_reports_nothing(self):
        r = rec(title="Mouse heart proteome",
                sampleProcessingProtocol="Samples were digested with trypsin overnight.")
        report = reconcile(r, self._rows(), "PXD000001")
        assert report.clean, report.render()
        assert "agrees with the deposit record" in report.render()

    def test_findings_are_ordered_and_rendered(self):
        r = rec(title="Proteomics of epicardial adipose tissue",
                sampleProcessingProtocol="Digested with trypsin.",
                quantificationMethods=["TMT"])
        report = reconcile(r, self._rows(), "PXD000002")
        assert not report.clean
        assert report.blockers
        assert report.render().splitlines()[0].startswith("PXD000002:")

    def test_empty_rows_are_safe(self):
        assert reconcile(rec(), [], "PXD000003").clean
