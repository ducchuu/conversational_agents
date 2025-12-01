import argparse
import json
from importlib.resources import files


def parse_arguments():
    """
    Parses command-line arguments for the NLU pipeline.

    Returns:
        argparse.Namespace: Parsed command-line arguments.
    """
    parser = argparse.ArgumentParser(description="NLU Model Training and Evaluation Pipeline")

    parser.add_argument("--ontology_path", type=str, default="./data/ontology.json",
                        help="Path to the ontology JSON file")
    parser.add_argument("--train_data", type=str, default="./data/train.json", help="Path to load train data")
    parser.add_argument("--test_data", type=str, default="./data/test.json", help="Path to load test data")
    parser.add_argument("--model_save_path", type=str, default="./checkpoints/model_checkpoint.pt",
                        help="Path to save/load model weights")

    parser.add_argument("--train_model", action="store_true", default=False, help="Train the model if this flag is set")
    parser.add_argument("--evaluate", action="store_true", default=False, help="Evaluate the model on test data if this flag is set")

    parser.add_argument("--num_epochs", type=int, default=2, help="Number of training epochs")
    parser.add_argument("--batch_size", type=int, default=16, help="Batch size for training")
    parser.add_argument("--learning_rate", type=float, default=5e-5, help="Learning rate for the optimizer")
    parser.add_argument("--max_length", type=int, default=16, help="Maximum sequence length for tokenization")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")

    parser.add_argument("--inference_text", type=str, default=None, help="Run inference on a single example text")

    parser.add_argument("--show_dist",  action="store_true", default=False, help="Shows the dataset distribution")
    #parser.add_argument("--prep_data", action="store_true", default=False, help="Prepare data for training")

    return parser.parse_args()


def load_synonyms():
    """
    Load the ontology (synonyms) from a default JSON file.

    Returns:
        dict: The loaded ontology dictionary.
    """
    print()
    ontology_path = str(files("sic_framework.services.nlu.utils.data").joinpath("synonyms.json"))  # Default path to the ontology
    with open(ontology_path, 'r') as f:
        return json.load(f)


def get_canonical_value(ontology, slot_type, slot_value):
    """
    Get the canonical value (key) from an ontology based on the slot type and slot value.

    Args:
        ontology (dict): The ontology dictionary.
        slot_type (str): The slot type (e.g., "cuisine", "duration").
        slot_value (str): The slot value to search for (e.g., "quick", "japan").

    Returns:
        str: The canonical value (key) corresponding to the slot value, or the original slot value if not found.
    """
    if slot_type not in ontology.keys():
        return slot_value.lower()

    slot_dict = ontology[slot_type]

    for key, synonyms in slot_dict.items():
        if slot_value.lower() in [syn.lower() for syn in synonyms]:
            return key  # Return the canonical value (key)

    return slot_value  # Return the original value if no match is found


def normalize_slots(slots):
    """
    Normalize the slot values in the prediction using the ontology.

    Args:
        slots (dict): The predicted slots from the model (e.g., {"cuisine": "japan", "duration": "fast"}).

    Returns:
        dict: Normalized slots with canonical values.
    """
    # Load ontology once (assumes default path)
    ontology = load_synonyms()

    normalized_slots = {}
    for slot_type, slot_value in slots.items():
        normalized_value = get_canonical_value(ontology, slot_type, slot_value)
        normalized_slots[slot_type] = normalized_value
    return normalized_slots


def extract_slots_from_text(slots_array, inference_text):
    """
    Extracts slot values directly from the slots array and inference text using index alignment.

    Args:
        slots_array (list): List of slot tags in BIO format.
        inference_text (str): Original input text.

    Returns:
        dict: Dictionary of slots and their corresponding values.
    """
    words = inference_text.split()  # Split the inference text into words
    slots_dict = {}
    current_slot_type = None
    current_slot_value = []

    for word, slot_tag in zip(words, slots_array):
        if slot_tag == "O":
            # If current slot ends, save it
            if current_slot_type and current_slot_value:
                slots_dict[current_slot_type] = " ".join(current_slot_value)
                current_slot_type = None
                current_slot_value = []
        elif slot_tag.startswith("B-"):
            # Save the previous slot if it exists
            if current_slot_type and current_slot_value:
                slots_dict[current_slot_type] = " ".join(current_slot_value)
            # Start a new slot
            current_slot_type = slot_tag[2:]
            current_slot_value = [word]
        elif slot_tag.startswith("I-") and current_slot_type == slot_tag[2:]:
            # Continue the current slot
            current_slot_value.append(word)

    # Add the last slot if it exists
    if current_slot_type and current_slot_value:
        slots_dict[current_slot_type] = " ".join(current_slot_value)

    return slots_dict

