import torch
import torch.nn as nn
from transformers import BertModel

class BERTNLUModel(nn.Module):
    """
    A BERT-based model for Natural Language Understanding (NLU), supporting intent classification
    and slot filling tasks.

    Architecture:
    - Base Model: Pre-trained `BertModel` for contextual embeddings.
    - Intent Classifier: A linear layer on top of the [CLS] token output for intent prediction.
    - Slot Classifier: A linear layer applied to token-level embeddings for slot tagging.

    Args:
        num_intents (int): Number of unique intents for classification.
        num_slots (int): Number of unique slot labels for tagging.

    Methods:
        forward(input_ids, attention_mask):
            Performs a forward pass to generate intent and slot logits.

            Args:
                input_ids (torch.Tensor): Token IDs (batch_size x seq_length).
                attention_mask (torch.Tensor): Attention mask (batch_size x seq_length).

            Returns:
                tuple:
                    intent_logits (torch.Tensor): Logits for intent classification (batch_size x num_intents).
                    slot_logits (torch.Tensor): Logits for slot tagging (batch_size x seq_length x num_slots).
    """
    def __init__(self, num_intents, num_slots):
        super(BERTNLUModel, self).__init__()
        # self.bert -> Initialize with BertModel.from_pretrained('bert-base-uncased')
        # self.intent_classifier -> Initialize as nn.Linear with appropriate dimensions
        # self.slot_classifier -> Initialize as nn.Linear with appropriate dimensions

        self.bert = BertModel.from_pretrained('bert-base-uncased')
        #hidden_size is for the input used, using conf. as it has to be exact
        self.intent_classifier = nn.Linear(self.bert.config.hidden_size,num_intents)
        self.slot_classifier = nn.Linear(self.bert.config.hidden_size,num_slots)






    def forward(self, input_ids, attention_mask):
        # outputs -> Call self.bert with input_ids and attention_mask as arguments
        outputs = self.bert(input_ids, attention_mask)

        # sequence_output -> Extract last_hidden_state from outputs
        sequence_output = outputs.last_hidden_state


        # pooled_output -> Extract pooler_output from outputs
        pooled_output = outputs.pooler_output

        # intent_logits -> Pass pooled_output through self.intent_classifier
        intent_logits = self.intent_classifier(pooled_output)

        # slot_logits -> Pass sequence_output through self.slot_classifier
        slot_logits = self.slot_classifier(sequence_output)

        return intent_logits, slot_logits # intent_logits, slot_logits