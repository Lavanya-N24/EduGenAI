from datasets import load_dataset
from transformers import AutoTokenizer
from transformers import AutoModelForSequenceClassification
from transformers import Trainer, TrainingArguments

dataset = load_dataset(
    "csv",
    data_files="dataset/train.csv"
)

model_name = "distilbert-base-uncased"

tokenizer = AutoTokenizer.from_pretrained(model_name)

def tokenize(example):

    return tokenizer(
        example["text"],
        truncation=True,
        padding="max_length"
    )

tokenized = dataset.map(tokenize)

model = AutoModelForSequenceClassification.from_pretrained(
    model_name,
    num_labels=2
)

training_args = TrainingArguments(
    output_dir="./models",
    num_train_epochs=5,
    per_device_train_batch_size=2,
    save_strategy="no",
    logging_steps=10,
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized["train"]
)

trainer.train()

model.save_pretrained("./models")
tokenizer.save_pretrained("./models")

print("[DONE] FILTER MODEL TRAINED")
