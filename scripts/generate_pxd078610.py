import json
import ssl
import urllib.request
from pathlib import Path


API_URL = "https://www.ebi.ac.uk/pride/ws/archive/v3/projects/PXD078610/files/all"
OUTPUT = Path("annotations/PXD078610.sdrf.tsv")


def main():
    context = ssl.create_default_context(cafile="/etc/ssl/cert.pem")
    with urllib.request.urlopen(API_URL, context=context) as response:
        files = json.load(response)

    raw_files = sorted(
        item["fileName"]
        for item in files
        if item.get("fileCategory", {}).get("value") == "RAW"
    )
    if len(raw_files) != 100:
        raise RuntimeError(f"Expected 100 raw files, found {len(raw_files)}")

    columns = [
        "source name",
        "characteristics[organism]",
        "characteristics[organism part]",
        "characteristics[disease]",
        "characteristics[material type]",
        "characteristics[sample type]",
        "characteristics[biological replicate]",
        "assay name",
        "technology type",
        "comment[instrument]",
        "comment[label]",
        "comment[modification parameters]",
        "comment[modification parameters]",
        "comment[cleavage agent details]",
        "comment[proteomics data acquisition method]",
        "comment[dissociation method]",
        "comment[collision energy]",
        "comment[precursor mass tolerance]",
        "comment[fragment mass tolerance]",
        "comment[fraction identifier]",
        "comment[technical replicate]",
        "comment[data file]",
        "comment[sdrf version]",
        "comment[sdrf template]",
        "comment[sdrf template]",
        "comment[sdrf template]",
        "factor value[disease]",
    ]
    group_replicates = {"CRC": 0, "HC": 0}
    rows = ["\t".join(columns)]
    for run_number, data_file in enumerate(raw_files, 1):
        group = "CRC" if "CRC" in data_file else "HC"
        group_replicates[group] += 1
        disease = (
            "NT=colorectal cancer;AC=MONDO:0005575"
            if group == "CRC"
            else "NT=normal;AC=PATO:0000461"
        )
        factor = "colorectal cancer" if group == "CRC" else "normal"
        rows.append(
            "\t".join(
                [
                    data_file.removesuffix(".raw"),
                    "NT=Homo sapiens;AC=NCBITaxon:9606",
                    "NT=saliva;AC=BTO:0001202",
                    disease,
                    "biofluid",
                    "NT=biofluid;AC=PRIDE:0000904",
                    str(group_replicates[group]),
                    f"run {run_number}",
                    "proteomic profiling by mass spectrometry",
                    "NT=Orbitrap Fusion;AC=MS:1002416",
                    "NT=label free sample;AC=MS:1002038",
                    "NT=Carbamidomethyl;AC=UNIMOD:4;TA=C;MT=Fixed",
                    "NT=Oxidation;AC=UNIMOD:35;TA=M;MT=Variable",
                    "NT=Trypsin;AC=MS:1001251",
                    "NT=Data-dependent acquisition;AC=PRIDE:0000627",
                    "NT=higher energy beam-type collision-induced dissociation;AC=MS:1002481",
                    "30% NCE",
                    "not available",
                    "not available",
                    "1",
                    "1",
                    data_file,
                    "v1.1.0",
                    "NT=ms-proteomics;VV=v1.1.0",
                    "NT=human;VV=v1.1.0",
                    "NT=clinical-metadata;VV=v1.0.0",
                    factor,
                ]
            )
        )

    OUTPUT.write_text("\n".join(rows) + "\n", encoding="utf-8")
    print(f"wrote {OUTPUT}: {len(rows) - 1} rows; {group_replicates}")


if __name__ == "__main__":
    main()