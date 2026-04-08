from dataclasses import dataclass, asdict
from typing import List, Dict
import pandas as pd
import re
import json
import hashlib
import unicodedata


@dataclass
class OccupationRecord:
    occupation_name: str
    competency: str
    ekr_level: int
    activity_indicators: str

@dataclass
class ActivityIndicatorData:
    id: str
    text: str
    code: str


@dataclass
class CompetencyData:
    id: str
    name: str
    ekr_level: int
    code: str
    activity_indicators: List[ActivityIndicatorData]


@dataclass
class OccupationData:
    id: str
    name: str
    competencies: List[CompetencyData]


def slugify(text: str) -> str:
    """
    Create a stable slug from text.
    Keeps Estonian letters readable by transliterating to ASCII where possible.
    """
    text = text.strip().lower()

    replacements = {
        "õ": "o",
        "ä": "a",
        "ö": "o",
        "ü": "u",
        "š": "s",
        "ž": "z",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)

    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")

    return text


def short_hash(text: str, length: int = 6) -> str:
    """
    Deterministic short hash for stable codes/IDs.
    """
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:length].upper()


def load_occupation_records(
    file_path: str,
    sheet_name: str | int = 0,
    field_filter: str | None = None,
) -> List[OccupationRecord]:

    # Map Excel column names -> Python field names
    column_map = {
        "Valdkond": "field",
        "Kutse grupp": "occupation_name",
        "Kompetents": "competency",
        "EKR\ntase": "ekr_level",
        "Tegevusnäitajad": "activity_indicators",
    }

    df = pd.read_excel(
        file_path,
        sheet_name=sheet_name,
        usecols=[
            "Valdkond",
            "Kutse grupp",
            "Kompetents",
            "EKR\ntase",
            "Tegevusnäitajad",
        ],
    )

    # Clean column names and rename
    df.columns = df.columns.str.strip()
    df.rename(columns=column_map, inplace=True)

    # Optional filter by field/domain
    if field_filter is not None:
        df["field"] = df["field"].astype(str).str.strip()
        df = df[df["field"] == field_filter].copy()

    # Drop rows where the important fields are empty
    df.dropna(subset=["occupation_name", "competency"], inplace=True)

    records: List[OccupationRecord] = []

    for _, row in df.iterrows():
        occupation_name = str(row["occupation_name"]).strip()
        competency = str(row["competency"]).strip()

        ekr_value = row["ekr_level"]
        if pd.isna(ekr_value):
            raise ValueError(
                f"Missing EKR level for occupation='{occupation_name}', competency='{competency}'"
            )

        try:
            ekr_level = int(float(ekr_value))
        except (ValueError, TypeError) as exc:
            raise ValueError(
                f"Invalid EKR level '{ekr_value}' for occupation='{occupation_name}', competency='{competency}'"
            ) from exc

        activity_indicators = ""
        if not pd.isna(row["activity_indicators"]):
            activity_indicators = str(row["activity_indicators"]).strip()

        records.append(
            OccupationRecord(
                occupation_name=occupation_name,
                competency=competency,
                ekr_level=ekr_level,
                activity_indicators=activity_indicators,
            )
        )

    return records

def parse_activity_indicators(raw_text: str, competency_slug: str) -> List[ActivityIndicatorData]:
    if not raw_text or not raw_text.strip():
        return []

    text = raw_text.strip()

    matches = re.findall(
        r"\d+\.\s*(.*?)(?=\n\d+\.|\Z)",
        text,
        flags=re.DOTALL
    )

    indicators: List[ActivityIndicatorData] = []

    for match in matches:
        cleaned = " ".join(match.split())
        if not cleaned:
            continue

        hash_input = f"{competency_slug}|{cleaned}"
        indicator_hash = short_hash(hash_input)

        indicators.append(
            ActivityIndicatorData(
                id=f"ai_{competency_slug}_{indicator_hash.lower()}",
                text=cleaned,
                code=f"AI-{indicator_hash}",
            )
        )

    return indicators


def occupation_record_to_competency_data(record: OccupationRecord) -> CompetencyData:
    competency_name = record.competency.strip()
    competency_slug = slugify(competency_name)
    competency_hash = short_hash(competency_name)

    return CompetencyData(
        id=f"comp_{competency_slug}",
        name=competency_name,
        ekr_level=record.ekr_level,
        code=f"COMP-{competency_hash}",
        activity_indicators=parse_activity_indicators(
            record.activity_indicators,
            competency_slug=competency_slug,
        ),
    )

def group_records_by_occupation(records: List[OccupationRecord]) -> List[OccupationData]:
    grouped: Dict[str, OccupationData] = {}

    for record in records:
        occupation_name = record.occupation_name.strip()
        occupation_slug = slugify(occupation_name)

        competency_data = occupation_record_to_competency_data(record)

        if occupation_name not in grouped:
            grouped[occupation_name] = OccupationData(
                id=f"occ_{occupation_slug}",
                name=occupation_name,
                competencies=[],
            )

        grouped[occupation_name].competencies.append(competency_data)

    return list(grouped.values())

def print_summary(occupation_data: List[OccupationData]) -> None:
    print(f"Total occupations: {len(occupation_data)}")

    total_competencies = sum(len(occ.competencies) for occ in occupation_data)
    total_indicators = sum(
        len(comp.activity_indicators)
        for occ in occupation_data
        for comp in occ.competencies
    )

    print(f"Total competencies: {total_competencies}")
    print(f"Total activity indicators: {total_indicators}")

def export_to_json(occupation_data: List[OccupationData], output_path: str) -> None:
    data = [asdict(occ) for occ in occupation_data]

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_occupation_data_from_excel(
    *,
    file_path: str,
    sheet_name: str | int = 0,
    field_filter: str | None = None,
) -> List[OccupationData]:
    records = load_occupation_records(file_path, sheet_name, field_filter)
    return group_records_by_occupation(records)


if __name__ == "__main__":
    
    excel_file = "kompetentsid.xlsx"
    records = load_occupation_records(
        excel_file,
        sheet_name=0,
        field_filter="IT, TELEKOMMUNIKATSIOON JA ELEKTROONIKA"
    )

    print(f"\nLoaded {len(records)} filtered records.")


    occupation_data = group_records_by_occupation(records)
    print(f"\nGrouped into {len(occupation_data)} occupations.")
    
    print_summary(occupation_data)
    #export_to_json(occupation_data, "it_occupations.json")
    """
    for occupation in occupation_data[:1]:
        print(f"\nOccupation: {occupation.name} ({occupation.id})")

        for comp in occupation.competencies:
            print(f"  Competency: {comp.name}")
            print(f"    id: {comp.id}")
            print(f"    code: {comp.code}")
            print(f"    ekr_level: {comp.ekr_level}")

            for idx, indicator in enumerate(comp.activity_indicators, start=1):
                print(f"    ActivityIndicator {idx}:")
                print(f"      text: {indicator.text}")
                print(f"      id:   {indicator.id}")
                print(f"      code: {indicator.code}")
    """