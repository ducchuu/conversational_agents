"""
data_processing.py

This module processes and prepares run_data for training and evaluation in an NLU pipeline. It supports:
1. Extracting intents and slots from Dialogflow JSON and CSV files.
2. Structuring and saving intents and slots as an ontology (JSON).
3. Loading, preprocessing, and splitting CSV run_data for intent classification and slot filling.
4. Extracting and structuring user utterances for training models.
5. Splitting structured run_data into train and test sets.

Functions:
- extract_intents: Extract intent names from JSON files in a directory.
- extract_slots: Extract slot values from CSV files in a directory.
- save_ontology: Save intents and slots as a JSON ontology file.
- split_csv_data: Split CSV run_data into train and test JSON files.
- extract_user_utterances: Structure user utterances from intent JSON files.
- split_user_utterances: Split structured utterances into train and test sets.

Ensure correct file paths for `intent_path` and `slot_path` are provided when calling functions.
"""

import os
import json
import csv
import random
import pandas as pd

def extract_intents(intent_path):
    """
    Extract intent names from JSON files in a directory.

    Args:
        intent_path (str): Directory path containing intent JSON files.

    Returns:
        list: Sorted list of intent names.
    """
    intents = []
    for file_name in os.listdir(intent_path):
        with open(os.path.join(intent_path, file_name), 'r', encoding='utf-8') as file:
            data = json.load(file)
            intents.append(data['name'].replace(' ', ''))
    return sorted(intents)

def extract_slots(slot_path):
    """
    Extract slot values from CSV files in a directory.

    Args:
        slot_path (str): Directory path containing slot CSV files.

    Returns:
        dict: Dictionary of slots with slot names as keys and unique slot values as lists.
    """
    slots = {}
    for file_name in os.listdir(slot_path):
        if file_name.endswith('.csv'):
            df = pd.read_csv(os.path.join(slot_path, file_name), header=None)
            name = file_name.split('.')[0]
            slots[name] = sorted(df.iloc[:, 0].dropna().unique().tolist())
    return slots

def save_ontology(intents, slots, output_path='ontology.json'):
    """
    Save intents and slots as a JSON ontology file.

    Args:
        intents (list): List of intent names.
        slots (dict): Dictionary of slots with values.
        output_path (str): File path to save the ontology JSON.
    """
    ontology = {'intents': intents, 'slots': slots}
    with open(output_path, 'w', encoding='utf-8') as file:
        json.dump(ontology, file, indent=4)

def split_csv_data(csv_file_path, train_file_path, test_file_path, train_ratio=0.8):
    """
    Split CSV run_data into train and test JSON files.

    Args:
        csv_file_path (str): Path to input CSV file.
        train_file_path (str): Path to save training JSON file.
        test_file_path (str): Path to save testing JSON file.
        train_ratio (float): Proportion of run_data for training (default 0.8).
    """
    data = []
    with open(csv_file_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            data.append({"text": row['text'], "intent": row['intent'], "slots": {}})
    random.shuffle(data)
    split_index = int(len(data) * train_ratio)
    with open(train_file_path, 'w', encoding='utf-8') as train_file:
        json.dump(data[:split_index], train_file, indent=4, ensure_ascii=False)
    with open(test_file_path, 'w', encoding='utf-8') as test_file:
        json.dump(data[split_index:], test_file, indent=4, ensure_ascii=False)

def extract_user_utterances(intent_path, ontology):
    """
    Extract and structure user utterances from JSON files.

    Args:
        intent_path (str): Directory path containing intent JSON files.
        ontology (dict): Ontology with slots for reference.

    Returns:
        list: Structured user utterances.
    """
    utterances = []
    for file_name in os.listdir(intent_path):
        with open(os.path.join(intent_path, file_name), 'r', encoding='utf-8') as file:
            data = json.load(file)
            for utterance in data.get('userSays', []):
                text_chunks = []
                slot_tags = {}
                for chunk in utterance['run_data']:
                    text_chunks.append(chunk['text'])
                    if 'meta' in chunk and chunk['meta'][1:] in ontology['slots']:
                        slot_tags[chunk['meta'][1:]] = chunk['text']
                utterances.append({
                    "id": utterance['id'],
                    "text": ' '.join(text_chunks),
                    "intent": file_name.split('.')[0].replace(' ', ''),
                    "slots": slot_tags
                })
    return utterances

def split_user_utterances(utterances, train_file_path, test_file_path, train_ratio=0.8):
    """
    Split structured user utterances into train and test sets.

    Args:
        utterances (list): Structured user utterances.
        train_file_path (str): Path to save training JSON file.
        test_file_path (str): Path to save testing JSON file.
        train_ratio (float): Proportion of run_data for training (default 0.8).
    """
    random.shuffle(utterances)
    split_index = int(len(utterances) * train_ratio)
    with open(train_file_path, 'w', encoding='utf-8') as train_file:
        json.dump(utterances[:split_index], train_file, indent=4, ensure_ascii=False)
    with open(test_file_path, 'w', encoding='utf-8') as test_file:
        json.dump(utterances[split_index:], test_file, indent=4, ensure_ascii=False)
