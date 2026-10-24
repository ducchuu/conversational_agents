import json
import re
from pathlib import Path
from collections import Counter

DATA_DIR = Path("sic_framework/services/nlu/utils/data")
ONTOLOGY_PATH = DATA_DIR / "ontology.json"
FILES_TO_AUDIT = [
    DATA_DIR / "exclusion_examples.json",
    DATA_DIR / "exclusion_examples_test.json",
]

POS_TO_NEG = {
    "ingredient": "excludeIngredient",
    "ingredientType": "excludeIngredient",
    "cuisine": "excludeCuisine",
    "tag": "excludeTag",
    "mealType": "excludeMealType",
}

NEG_TO_POS = {
    "excludeIngredient": "ingredient",
    "excludeCuisine": "cuisine",
    "excludeTag": "tag",
    "excludeMealType": "mealType",
}

DURATION_NOISE_PATTERN = re.compile(
    r"\b(no|not|never)\s+(longer|more|less|greater|higher|later)\s+than\b|"
    r"\bdoes not take (more|longer|less) than\b|"
    r"\bnon\s+gluten[- ]free\b",
    re.IGNORECASE,
)

NEGATION_PATTERN = re.compile(
    r"\b(without|no|not|never|ni|nor|none|exclude|excluding|except|avoid|avoiding|"
    r"free of|free from|other than|anything but|allergic|allergy|intolerant|intolerance|"
    r"don't|do not|doesn't|does not|didn't|did not|won't|will not|wouldn't|would not|"
    r"can't|cannot|couldn't|could not|shouldn't|should not|must not|mustn't|"
    r"hate|hates|dislike|dislikes|instead of|rather than|not into|sick of|tired of|"
    r"hold|skip|skipping|leave out|leaving out|omitting|omit|pass on|stay away from|"
    r"zero|less|minus|rid of|ban|drop|remove|unwanted|cut out)\b",
    re.IGNORECASE,
)

POST_NEGATION_PATTERN = re.compile(
    r"^\s*(-|\s)*(free\b|less\b|is a no\b|is out\b|not very\b|is not\b|aren't\b|isn't\b|"
    r"cuisines not\b|cuisine is not\b|food is out\b|please no\b)|"
    r"\b(without|no|not|avoid|skip|hate|dislike)\s+(it|them|that|those)\b",
    re.IGNORECASE,
)

CLAUSE_POSITIVE_RESTART = re.compile(
    r"((\b(and|but|yet|however|though|although|while)\b|[,;])\s*"
    r"(i\s+(want|would like|need|prefer|love|like|said i want|am in the mood for)\s+|"
    r"(loves|likes|wants|needs|prefers)\s+|"
    r"(with|containing|contains|includes|including|that has|that have|has|have|having|using|is|for|to)\b))|"
    r"\b(with|in|on|for)\s+(my|the|a|an)\b|"
    r"\bi said i want\b|"
    r"\binstead of\s+[\w\s]+?\s+(i want|give me|with|use)\b",
    re.IGNORECASE,
)


def is_value_negated(text: str, value: str) -> bool:
    cleaned_text = DURATION_NOISE_PATTERN.sub(" ", text.lower())
    val_lower = str(value).lower().strip()
    idx = cleaned_text.find(val_lower)

    if idx == -1:
        return bool(NEGATION_PATTERN.search(cleaned_text))

    prefix = cleaned_text[:idx]
    suffix = cleaned_text[idx + len(val_lower) :]

    if POST_NEGATION_PATTERN.search(suffix):
        if not re.search(r"\bi said i want\b", prefix):
            return True

    sentences = re.split(r"[.!?]", prefix)
    current_sentence = sentences[-1]

    neg_matches = list(NEGATION_PATTERN.finditer(current_sentence))
    if not neg_matches:
        if re.search(r"\b(allergic|allergy|intolerant|intolerance)\b", cleaned_text):
            if not re.search(r"\b(want|like|love|with|need)\b", current_sentence):
                return True
        return False

    last_neg = neg_matches[-1]
    intervening_text = current_sentence[last_neg.end() :]

    if CLAUSE_POSITIVE_RESTART.search(intervening_text):
        return False

    return True


def add_slot_value(slots: dict, key: str, val: str):
    if key not in slots:
        slots[key] = val
        return

    existing = slots[key]
    if isinstance(existing, list):
        if val not in existing:
            existing.append(val)
    else:
        if existing != val:
            slots[key] = [existing, val]


def update_ontology(observed_tags: set, apply_fix: bool = False):
    if not ONTOLOGY_PATH.exists():
        print(f"Ontology file not found at {ONTOLOGY_PATH}")
        return

    with open(ONTOLOGY_PATH, "r", encoding="utf-8") as f:
        ont = json.load(f)

    target_dict = ont["slots"] if "slots" in ont and isinstance(ont["slots"], dict) else ont
    current_tags = set(target_dict.get("tag", []))
    missing_tags = sorted(
        t for t in observed_tags if t.lower() not in {ct.lower() for ct in current_tags}
    )

    print("=== Ontology Audit ===")
    print(f"Current 'tag' count in ontology.json: {len(current_tags)}")
    print(f"Has 'excludeTag' in ontology.json: {'excludeTag' in target_dict}")
    print(f"Tag values in exclusion datasets missing from ontology 'tag' ({len(missing_tags)}):")
    print(f"  {missing_tags}\n")

    if apply_fix:
        merged_tags = list(target_dict.get("tag", []))
        for t in missing_tags:
            if t not in merged_tags:
                merged_tags.append(t)
        target_dict["tag"] = merged_tags
        target_dict["excludeTag"] = list(merged_tags)
        with open(ONTOLOGY_PATH, "w", encoding="utf-8") as f:
            json.dump(ont, f, indent=4, ensure_ascii=False)
        print(f"Updated {ONTOLOGY_PATH} with 'excludeTag' and {len(missing_tags)} missing tag values.\n")


def audit_and_fix_file(filepath: Path, observed_tags: set, apply_fix: bool = False):
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    stats = Counter()
    intent_counts = Counter()
    slot_key_counts_before = Counter()
    slot_key_counts_after = Counter()
    flagged_examples = []
    no_exclusion_left = []

    for item in data:
        text = item.get("text", "")
        intent = item.get("intent", "")
        slots = item.get("slots", {})
        intent_counts[intent] += 1

        for k, v in slots.items():
            slot_key_counts_before[k] += 1
            if k in ("tag", "excludeTag"):
                vals = v if isinstance(v, list) else [v]
                for sv in vals:
                    observed_tags.add(str(sv).strip())

        if intent != "addFilter" or not slots:
            for k in slots.keys():
                slot_key_counts_after[k] += 1
            continue

        new_slots = {}
        modified = False
        changes_desc = []

        for k, v in list(slots.items()):
            values = v if isinstance(v, list) else [v]

            for single_val in values:
                if k in POS_TO_NEG:
                    if is_value_negated(text, single_val):
                        target_key = POS_TO_NEG[k]
                        add_slot_value(new_slots, target_key, single_val)
                        modified = True
                        stats[f"{k} -> {target_key}"] += 1
                        changes_desc.append(f"{k}:{single_val} -> {target_key}:{single_val}")
                    else:
                        add_slot_value(new_slots, k, single_val)

                elif k in NEG_TO_POS:
                    if not is_value_negated(text, single_val):
                        target_key = NEG_TO_POS[k]
                        add_slot_value(new_slots, target_key, single_val)
                        modified = True
                        stats[f"{k} -> {target_key}"] += 1
                        changes_desc.append(f"{k}:{single_val} -> {target_key}:{single_val}")
                    else:
                        add_slot_value(new_slots, k, single_val)

                else:
                    add_slot_value(new_slots, k, single_val)

        if modified:
            flagged_examples.append(
                {
                    "id": item.get("id"),
                    "text": text,
                    "old_slots": slots,
                    "new_slots": new_slots,
                    "changes": changes_desc,
                }
            )
            if apply_fix:
                item["slots"] = new_slots

        final_slots = new_slots if modified else slots
        for k in final_slots.keys():
            slot_key_counts_after[k] += 1

        if not any(k.startswith("exclude") for k in final_slots.keys()):
            no_exclusion_left.append(
                {
                    "id": item.get("id"),
                    "text": text,
                    "slots": final_slots,
                }
            )

    print(f"==================================================")
    print(f"Audit Report for {filepath.name}")
    print(f"==================================================")
    print(f"Total records scanned: {len(data)}")
    print(f"Intents distribution: {dict(intent_counts)}")
    print(f"Slot distribution BEFORE: {dict(slot_key_counts_before.most_common())}")
    print(f"Slot distribution AFTER:  {dict(slot_key_counts_after.most_common())}")
    print(f"\nTotal records modified: {len(flagged_examples)}")
    for transition, count in stats.most_common():
        print(f"  {transition}: {count}")

    tag_fixes = [s for s in flagged_examples if any("tag" in c.lower() for c in s["changes"])]
    print(f"\nSample 'tag <-> excludeTag' fixes (up to 10 of {len(tag_fixes)}):")
    for sample in tag_fixes[:10]:
        print(f"  [{sample['id']}] \"{sample['text']}\"")
        print(f"     {sample['old_slots']}  ==>  {sample['new_slots']}")

    print(f"\nRemaining records with ZERO exclude* slots: {len(no_exclusion_left)}")
    for rem in no_exclusion_left[:25]:
        print(f"  [{rem['id']}] \"{rem['text']}\" -> {rem['slots']}")
    print()

    if apply_fix and flagged_examples:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Successfully wrote updated dataset to {filepath}\n")


if __name__ == "__main__":
    APPLY_FIX = True
    observed_tags = set()

    for path in FILES_TO_AUDIT:
        if path.exists():
            audit_and_fix_file(path, observed_tags, apply_fix=APPLY_FIX)

    update_ontology(observed_tags, apply_fix=APPLY_FIX)
