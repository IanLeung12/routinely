"""Guard the skeleton-only storage boundary and review-only product wording."""

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BANNED_PROPERTY = re.compile(r"image|frame_bytes|jpeg|png|video|pixels|base64", re.IGNORECASE)
BASE64_RUN = re.compile(r"[A-Za-z0-9+/=]{200,}")
NEGATED_WORDING = re.compile(r"\b(?:never|not)\s+diagnos\w*", re.IGNORECASE)


def schema_offenders(node, location):
    offenders = []
    if isinstance(node, dict):
        for key, value in node.items():
            child_location = f"{location}/{key}"
            if key.lower() == "contentencoding":
                offenders.append(child_location)
            if key == "properties" and isinstance(value, dict):
                offenders.extend(
                    f"{child_location}/{name}" for name in value if BANNED_PROPERTY.search(name)
                )
            offenders.extend(schema_offenders(value, child_location))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            offenders.extend(schema_offenders(value, f"{location}/{index}"))
    return offenders


def test_contract_schemas_cannot_carry_images():
    paths = sorted((REPO / "contracts").glob("*.schema.json"))
    assert paths, "No contract schemas found"
    offenders = []
    for path in paths:
        offenders.extend(schema_offenders(json.loads(path.read_text()), path.name))
    assert not offenders, "Image-bearing schema fields:\n" + "\n".join(offenders)


def test_recorded_jsonl_contains_only_small_non_image_payloads():
    paths = sorted((REPO / "tests/scenarios").glob("*/*.jsonl"))
    paths += sorted((REPO / "contracts/examples").glob("*.jsonl"))
    assert paths, "No JSONL recordings found"
    offenders = []
    for path in paths:
        for number, line in enumerate(path.read_bytes().splitlines(), start=1):
            location = f"{path.relative_to(REPO)}:{number}"
            if len(line) >= 20_000:
                offenders.append(f"{location}: line is {len(line)} bytes (must be < 20 kB)")
            text = line.decode("utf-8")
            if "data:image" in text.lower() or BASE64_RUN.search(text):
                offenders.append(f"{location}: image data or long base64-like run")
    assert not offenders, "Unsafe recording payloads:\n" + "\n".join(offenders)


def test_product_wording_flags_changes_for_review():
    offenders = []
    for root in (REPO / "pipeline/src", REPO / "web/src"):
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            if "__pycache__" in path.parts or "tests" in path.parts:
                continue
            if path.name.startswith("test_") or re.search(r"\.(?:test|spec)\.", path.name):
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue  # Binary assets have no product wording.
            for number, line in enumerate(text.splitlines(), start=1):
                if re.search(r"diagnos", NEGATED_WORDING.sub("", line), re.IGNORECASE):
                    offenders.append(f"{path.relative_to(REPO)}:{number}: {line.strip()}")
    assert not offenders, "Product wording must flag changes for review:\n" + "\n".join(offenders)
