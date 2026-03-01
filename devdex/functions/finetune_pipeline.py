from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def export_training_data(
    supabase_url: str,
    supabase_key: str,
    mistral_api_key: str,
    output_path: str | Path = "devdex_training.jsonl",
    min_rating: int = 4,
    min_samples: int = 50,
    validation_split: float = 0.2,
) -> tuple[Path, Path | None]:
    import random

    from devdex.functions.vector_store import VectorStore

    vs = VectorStore(supabase_url, supabase_key, mistral_api_key)

    try:
        records = vs.get_training_data(min_rating=min_rating, limit=5000)
    except Exception as e:
        raise ValueError(f"Failed to fetch training data from Supabase: {e}") from e

    if len(records) < min_samples:
        raise ValueError(
            f"Only {len(records)} training samples found "
            f"(need at least {min_samples}). Collect more feedback first."
        )

    entries = []
    for rec in records:
        system_prompt = rec.get("system_prompt", "")
        user_prompt = rec.get("user_prompt", "")
        content = rec.get("generated_content", "")

        if not system_prompt or not user_prompt or not content:
            continue

        combined_user = f"{system_prompt}\n\n{user_prompt}"

        entries.append({
            "messages": [
                {"role": "user", "content": combined_user},
                {"role": "assistant", "content": content},
            ]
        })

    random.shuffle(entries)

    output_path = Path(output_path)

    val_path = None
    if len(entries) >= 10 and validation_split > 0:
        split_idx = max(1, int(len(entries) * (1 - validation_split)))
        train_entries = entries[:split_idx]
        val_entries = entries[split_idx:]

        val_path = output_path.with_name(
            output_path.stem + "_validation" + output_path.suffix
        )
        with val_path.open("w") as f:
            for entry in val_entries:
                f.write(json.dumps(entry) + "\n")
        logger.info("Wrote %d validation samples to %s", len(val_entries), val_path)
    else:
        train_entries = entries

    with output_path.open("w") as f:
        for entry in train_entries:
            f.write(json.dumps(entry) + "\n")

    logger.info("Exported %d training samples to %s", len(train_entries), output_path)
    return output_path, val_path


def run_finetune(
    training_data_path: str | Path,
    validation_data_path: str | Path | None = None,
    base_model: str = "open-mistral-nemo",
    mistral_api_key: str = "",
    training_steps: int = 100,
    learning_rate: float = 0.0001,
    wandb_api_key: str = "",
) -> dict[str, Any]:
    from mistralai import Mistral

    client = Mistral(api_key=mistral_api_key)
    training_data_path = Path(training_data_path)

    with training_data_path.open("rb") as f:
        training_file = client.files.upload(
            file={"file_name": training_data_path.name, "content": f}
        )
    logger.info("Uploaded training file: %s", training_file.id)

    validation_files = None
    if validation_data_path:
        validation_data_path = Path(validation_data_path)
        if validation_data_path.exists():
            with validation_data_path.open("rb") as f:
                val_file = client.files.upload(
                    file={"file_name": validation_data_path.name, "content": f}
                )
            validation_files = [val_file.id]
            logger.info("Uploaded validation file: %s", val_file.id)

    job_kwargs: dict[str, Any] = {
        "model": base_model,
        "training_files": [{"file_id": training_file.id, "weight": 1}],
        "hyperparameters": {
            "training_steps": training_steps,
            "learning_rate": learning_rate,
        },
        "auto_start": False,
    }
    if validation_files:
        job_kwargs["validation_files"] = validation_files

    if wandb_api_key:
        job_kwargs["integrations"] = [
            {
                "type": "wandb",
                "project": "devdex-finetune",
                "api_key": wandb_api_key,
            }
        ]

    job = client.fine_tuning.jobs.create(**job_kwargs)
    logger.info("Fine-tuning job created: %s (status: %s)", job.id, job.status)

    if job.status in ("QUEUED", "VALIDATED"):
        job = client.fine_tuning.jobs.start(job_id=job.id)
        logger.info("Fine-tuning job started: %s", job.id)

    return {
        "job_id": job.id,
        "status": job.status,
        "fine_tuned_model": getattr(job, "fine_tuned_model", None),
    }


def poll_job_status(
    mistral_api_key: str,
    job_id: str,
    poll_interval: int = 30,
    max_wait: int = 3600,
) -> dict[str, Any]:
    from mistralai import Mistral

    client = Mistral(api_key=mistral_api_key)
    elapsed = 0

    while elapsed < max_wait:
        job = client.fine_tuning.jobs.get(job_id=job_id)

        if job.status == "SUCCESS":
            return {
                "job_id": job.id,
                "status": "SUCCESS",
                "fine_tuned_model": job.fine_tuned_model,
            }
        elif job.status in ("FAILED", "CANCELLED"):
            raise RuntimeError(
                f"Fine-tuning job {job_id} {job.status}"
            )

        time.sleep(poll_interval)
        elapsed += poll_interval

    raise TimeoutError(
        f"Fine-tuning job {job_id} did not complete within {max_wait}s"
    )


def register_model_version(
    model_id: str,
    job_id: str,
    wandb_api_key: str = "",
    base_model: str = "",
    training_samples: int = 0,
) -> None:
    if not wandb_api_key:
        logger.info("No W&B key — skipping model registration")
        return

    try:
        import wandb

        wandb.login(key=wandb_api_key)
        run = wandb.init(
            project="devdex-models",
            job_type="register",
            settings=wandb.Settings(silent=True, console="off"),
        )

        artifact = wandb.Artifact(
            name="devdex-finetuned",
            type="model",
            metadata={
                "model_id": model_id,
                "job_id": job_id,
                "base_model": base_model,
                "training_samples": training_samples,
            },
        )
        run.log_artifact(artifact)
        run.finish(quiet=True)

        logger.info("Registered model %s in W&B", model_id)
    except Exception as e:
        logger.debug("W&B model registration failed: %s", e)


def prepare_mlx_data_dir(
    training_data_path: str | Path,
    validation_data_path: str | Path | None = None,
) -> Path:
    import shutil

    training_data_path = Path(training_data_path)
    data_dir = training_data_path.parent / "mlx_data"
    data_dir.mkdir(exist_ok=True)

    shutil.copy2(training_data_path, data_dir / "train.jsonl")

    if validation_data_path:
        validation_data_path = Path(validation_data_path)
        if validation_data_path.exists():
            shutil.copy2(validation_data_path, data_dir / "valid.jsonl")

    return data_dir


def run_mlx_finetune(
    training_data_path: str | Path,
    validation_data_path: str | Path | None = None,
    base_model: str = "mlx-community/Mistral-7B-Instruct-v0.3-4bit",
    output_dir: str = "./devdex-mlx-adapters",
    iters: int = 100,
    batch_size: int = 1,
    num_layers: int = 4,
    learning_rate: float = 1e-5,
    wandb_api_key: str = "",
) -> str:
    import subprocess
    import sys

    data_dir = prepare_mlx_data_dir(training_data_path, validation_data_path)

    cmd = [
        sys.executable, "-m", "mlx_lm", "lora",
        "--model", base_model,
        "--data", str(data_dir),
        "--train",
        "--adapter-path", output_dir,
        "--iters", str(iters),
        "--batch-size", str(batch_size),
        "--num-layers", str(num_layers),
        "--learning-rate", str(learning_rate),
        "--grad-checkpoint",
    ]

    if wandb_api_key:
        cmd.extend(["--report-to", "wandb", "--project-name", "devdex-finetune"])

    logger.info("Running MLX fine-tuning: %s", " ".join(cmd))

    subprocess.run(cmd, check=True)

    logger.info("MLX fine-tuning complete. Adapters saved to %s", output_dir)
    return output_dir


def mlx_generate(
    base_model: str,
    adapter_path: str,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 2048,
) -> str:
    from mlx_lm import generate, load

    model, tokenizer = load(base_model, adapter_path=adapter_path)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    if hasattr(tokenizer, "apply_chat_template"):
        prompt = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
    else:
        prompt = f"{system_prompt}\n\nUser: {user_prompt}\nAssistant:"

    response = generate(model, tokenizer, prompt=prompt, max_tokens=max_tokens)
    return response


def run_unsloth_finetune(
    training_data_path: str | Path,
    base_model: str = "unsloth/mistral-7b-instruct-v0.3-bnb-4bit",
    output_dir: str = "./devdex-unsloth-finetuned",
    num_epochs: int = 1,
    max_steps: int = 100,
    learning_rate: float = 2e-4,
    max_seq_length: int = 2048,
    wandb_api_key: str = "",
) -> str:
    from unsloth import FastLanguageModel

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=base_model,
        max_seq_length=max_seq_length,
        load_in_4bit=True,
    )

    model = FastLanguageModel.get_peft_model(
        model,
        r=16,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                         "gate_proj", "up_proj", "down_proj"],
        lora_alpha=16,
        lora_dropout=0,
        use_gradient_checkpointing="unsloth",
    )

    from datasets import load_dataset
    from trl import SFTConfig, SFTTrainer

    dataset = load_dataset("json", data_files=str(training_data_path), split="train")

    def format_chat(example):
        text = tokenizer.apply_chat_template(
            example["messages"], tokenize=False, add_generation_prompt=False
        )
        return {"text": text}

    dataset = dataset.map(format_chat)

    report_to = "wandb" if wandb_api_key else "none"
    if wandb_api_key:
        import os
        os.environ["WANDB_API_KEY"] = wandb_api_key
        os.environ["WANDB_PROJECT"] = "devdex-finetune"

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        args=SFTConfig(
            output_dir=output_dir,
            per_device_train_batch_size=2,
            gradient_accumulation_steps=4,
            warmup_steps=5,
            max_steps=max_steps,
            num_train_epochs=num_epochs,
            learning_rate=learning_rate,
            fp16=True,
            logging_steps=1,
            save_strategy="steps",
            save_steps=max_steps,
            report_to=report_to,
            dataset_text_field="text",
            max_seq_length=max_seq_length,
            packing=False,
        ),
    )

    trainer.train()
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)

    logger.info("Unsloth fine-tuning complete. Model saved to %s", output_dir)
    return output_dir


def get_devdex_generator_class():
    try:
        import weave

        class DevDexGenerator(weave.Model):
            model: str
            artifact_type: str

            @weave.op()
            def predict(self, project_context: dict) -> str:
                from openai import OpenAI

                client = OpenAI(
                    base_url=project_context.get("base_url", ""),
                    api_key=project_context.get("api_key", ""),
                )
                response = client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": project_context.get("system_prompt", "")},
                        {"role": "user", "content": project_context.get("user_prompt", "")},
                    ],
                )
                return response.choices[0].message.content

        return DevDexGenerator
    except ImportError:
        return None


def run_local_finetune(
    training_data_path: str | Path,
    base_model: str = "mistralai/Ministral-8B-Instruct-2410",
    output_dir: str = "./devdex-finetuned",
    num_epochs: int = 3,
    learning_rate: float = 1e-4,
) -> str:
    from datasets import load_dataset
    from peft import LoraConfig, TaskType
    from trl import SFTConfig, SFTTrainer

    peft_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=16,
        lora_alpha=32,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
    )

    sft_config = SFTConfig(
        output_dir=output_dir,
        learning_rate=learning_rate,
        num_train_epochs=num_epochs,
        packing=True,
    )

    dataset = load_dataset("json", data_files=str(training_data_path), split="train")

    trainer = SFTTrainer(
        model=base_model,
        args=sft_config,
        peft_config=peft_config,
        train_dataset=dataset,
    )

    trainer.train()
    trainer.save_model(output_dir)

    logger.info("Local fine-tuning complete. Model saved to %s", output_dir)
    return output_dir
