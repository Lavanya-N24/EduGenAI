from transformers import T5Tokenizer, T5ForConditionalGeneration, Trainer, TrainingArguments
from datasets import load_dataset

print("Loading dataset...")
dataset = load_dataset("json", data_files="dataset/train.json")

print("Loading model...")
tokenizer = T5Tokenizer.from_pretrained("t5-small")
model = T5ForConditionalGeneration.from_pretrained("t5-small")

def preprocess(example):
    input_texts = ["generate question: " + c for c in example["context"]]
    target_texts = example["question"]

    inputs = tokenizer(input_texts, truncation=True, padding="max_length", max_length=128)
    targets = tokenizer(target_texts, truncation=True, padding="max_length", max_length=64)

    inputs["labels"] = targets["input_ids"]
    return inputs

print("Processing...")
tokenized = dataset.map(preprocess, batched=True)

print("Training...")
training_args = TrainingArguments(
    output_dir="./models/quiz_model",
    num_train_epochs=5,
    per_device_train_batch_size=1,
    save_strategy="no",
    logging_steps=10,
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized["train"]
)

trainer.train()

print("Saving...")
model.save_pretrained("./models/quiz_model")
tokenizer.save_pretrained("./models/quiz_model")

print("[DONE] QUIZ MODEL DONE")
