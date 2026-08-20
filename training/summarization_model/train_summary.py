from transformers import T5Tokenizer
from transformers import T5ForConditionalGeneration
from transformers import Trainer, TrainingArguments
from datasets import load_dataset

dataset = load_dataset(
    "json",
    data_files="dataset/train.json"
)

model_name = "t5-small"

tokenizer = T5Tokenizer.from_pretrained(model_name)

model = T5ForConditionalGeneration.from_pretrained(
    model_name
)

def preprocess(example):
    input_text = "summarize: " + example["text"]

    model_inputs = tokenizer(
        input_text,
        truncation=True,
        padding="max_length",
        max_length=512
    )

    labels = tokenizer(
        example["summary"],
        truncation=True,
        padding="max_length",
        max_length=128
    )

    model_inputs["labels"] = labels["input_ids"]
    return model_inputs

tokenized = dataset.map(preprocess)

training_args = TrainingArguments(
    output_dir="./models",
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

model.save_pretrained("./models")
tokenizer.save_pretrained("./models")

print("[DONE] SUMMARY MODEL TRAINED")
