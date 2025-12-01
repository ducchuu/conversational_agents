"""
This script implements a complete pipeline for training, evaluating, and running inference on a Natural Language
Understanding (NLU) model for intent classification and slot filling tasks.

Modules Used:
- Dataset preparation and preprocessing (`dataset` module)
- Model architecture (`intent_slot_classification_model` module)
- Training routines (`train` module)
- Evaluation and prediction (`evaluation` module)
"""

import torch
import numpy as np
import time
import random
from collections import Counter
from sic_framework.services.nlu.utils.dataset import load_ontology, load_data, preprocess_data, NLURecipeDataset, fit_encoders, intent_label_encoder, slot_label_encoder
from sic_framework.services.nlu.utils.train import train_model
from sic_framework.services.nlu.utils.evaluation import evaluate
from sic_framework.services.nlu.utils.predict import predict
from sic_framework.services.nlu.utils.model import BERTNLUModel
from sic_framework.services.nlu.utils.utils import parse_arguments


def analyze_distribution(data):
    """
    Analyzes the distribution of intents and slots in the given dataset.

    Args:
        data (list of dict): The dataset, where each item contains 'intent' and 'slots'.

    Returns:
        tuple: Two `Counter` objects, one for intent distribution and one for slot distribution.
    """
    # Extract intents from the dataset (list comprehension over item['intent'])
    # intents -> List of intents from the data

    # Extract slots from the dataset (nested list comprehension over item['slots'])
    # slots -> Flattened list of all slots from the data

    # Count the frequency of each intent using Counter
    # intent_distribution -> Use Counter on the intents list

    # Count the frequency of each slot using Counter
    # slot_distribution -> Use Counter on the slots list

    # Return intent_distribution and slot_distribution as a tuple
    # return intent_distribution, slot_distribution



def main():
    """
    Main function to orchestrate the NLU pipeline, including training, evaluation, and inference.
    """
    # Parse command-line arguments
    args = parse_arguments()

    # Set the seed for reproducibility
    SEED = args.seed
    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(SEED)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # Load ontology and fit encoders
    ontology_path = args.ontology_path
    ontology = load_ontology(ontology_path)

    fit_encoders(args.ontology_path)

    intent_classes =  intent_label_encoder.classes_
    slot_classes =  slot_label_encoder.classes_

    num_intents = len(intent_classes)
    num_slots = len(slot_classes )


    print("Loading and preprocessing data...")
    train_data = load_data(args.train_data)
    test_data = load_data(args.test_data)

    processed_train_data = preprocess_data(train_data, max_length=args.max_length)
    processed_test_data = preprocess_data(test_data, max_length=args.max_length)

    train_dataset = NLURecipeDataset(processed_train_data, ontology, max_length=args.max_length)
    test_dataset = NLURecipeDataset(processed_test_data, ontology, max_length=args.max_length)
    print(f"Finished data loading and preprocessing.")

    if args.show_dist:
        intent_dist, slot_dist = analyze_distribution(train_data)
        print("Training Intent Distribution:", intent_dist)
        print("Training Slot Distribution:", slot_dist)

        intent_dist, slot_dist = analyze_distribution(test_data)
        print("Test Intent Distribution:", intent_dist)
        print("Test Slot Distribution:", slot_dist)


    # Train the model
    if args.train_model:
        print("Training the model...")
        model = BERTNLUModel(num_intents=num_intents, num_slots=num_slots).to(device)

        start_time = time.time()
        model = train_model(
            model=model,
            dataset=train_dataset,
            num_epochs=args.num_epochs,
            batch_size=args.batch_size,
            learning_rate=args.learning_rate,
            device=device
        )
        print(f"Training the model took {time.time() - start_time:.2f} seconds.")

        torch.save(model.state_dict(), args.model_save_path)
        print(f"Model saved to {args.model_save_path}")

    # Evaluate the model
    if args.evaluate:
        print("Loading model for evaluation...")
        model = BERTNLUModel(num_intents=num_intents, num_slots=num_slots).to(device)
        model.load_state_dict(torch.load(args.model_save_path, weights_only=True))

        metrics = evaluate(model, test_dataset,
                           intent_classes, slot_classes, slot_label_encoder, device=device)
        print("Evaluation Metrics:", metrics)

    # Inference on a single example
    if args.inference_text:
        print(f"Running inference on example text: {args.inference_text}")
        model = BERTNLUModel(num_intents=num_intents, num_slots=num_slots).to(device)
        model.load_state_dict(torch.load(args.model_save_path, weights_only=True))

        # Predict intent and slots
        intent, intent_confidence, normalized_slots, slot_confidences = predict(model, args.inference_text, max_length=args.max_length, device=device)

        print("Inference Results:", intent, intent_confidence, normalized_slots)


if __name__ == "__main__":
    main()