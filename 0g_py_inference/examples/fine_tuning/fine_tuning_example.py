"""
0G Fine-Tuning SDK Example

This script demonstrates the full end-to-end fine-tuning workflow:
1. Create broker and connect to testnet
2. Deposit funds to the ledger
3. Transfer funds to the fine-tuning provider
4. Acknowledge the provider's TEE signer
5. Upload dataset to the TEE
6. Create a fine-tuning task
7. Monitor training progress

Prerequisites:
    pip install 0g-inference-sdk

Usage:
    export PRIVATE_KEY="0xYourPrivateKeyHere"
    python fine_tuning_example.py
"""

import os
import sys
import time
import json

from zerog_py_sdk import create_broker


# --- Configuration ---

PRIVATE_KEY = os.environ.get("PRIVATE_KEY", "")
NETWORK = "testnet"

# Fine-tuning provider address (from list_service)
PROVIDER_ADDRESS = "0xA02b95Aa6886b1116C4f334eDe00381511E31A09"

# Model to fine-tune (use list_service or list_model to discover available models)
MODEL_NAME = "Qwen2.5-0.5B-Instruct"

# Paths to dataset and training config (relative to this script)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_PATH = os.path.join(SCRIPT_DIR, "test_dataset.jsonl")
TRAINING_PARAMS_PATH = os.path.join(SCRIPT_DIR, "training_params.json")

# Amount to deposit/transfer (in A0GI).
# add_ledger requires at least 3 0G (contract MIN_ACCOUNT_BALANCE).
# transfer_fund's recommended minimum is 1 0G (broker proxy MinimumLockedBalance).
DEPOSIT_AMOUNT = "3"
TRANSFER_AMOUNT = "1"


def main():
    if not PRIVATE_KEY:
        print("Error: Set PRIVATE_KEY environment variable")
        print('  export PRIVATE_KEY="0xYourPrivateKeyHere"')
        sys.exit(1)

    # Step 1: Create broker
    print("Step 1: Creating broker...")
    broker = create_broker(private_key=PRIVATE_KEY, network=NETWORK)
    print(f"  Address: {broker.get_address()}")

    # Step 2: List available fine-tuning providers
    print("\nStep 2: Listing fine-tuning providers...")
    services = broker.fine_tuning.list_service()
    if not services:
        print("  No fine-tuning providers available!")
        sys.exit(1)
    for s in services:
        print(f"  Provider: {s.provider}")
        print(f"  URL: {s.url}")
        print(f"  Models: {s.models}")
        print(f"  Price per token: {s.price_per_token}")
        print()

    # Step 3: Deposit funds to ledger (if needed)
    print("Step 3: Checking ledger balance...")
    ledger_exists = False
    try:
        ledger = broker.ledger.get_ledger()
        ledger_exists = True
        available = ledger.available / 10**18
        total = ledger.total_balance / 10**18
        print(f"  Ledger exists: available={available:.6f}, total={total:.6f} A0GI")

        if available < 1.0:
            print(f"  Low balance, depositing {DEPOSIT_AMOUNT} A0GI...")
            broker.ledger.deposit_fund(DEPOSIT_AMOUNT)
            print("  Deposit successful!")
    except Exception:
        if not ledger_exists:
            print(f"  No ledger found, creating with {DEPOSIT_AMOUNT} A0GI...")
            broker.ledger.add_ledger(DEPOSIT_AMOUNT)
            print("  Ledger created!")

    # Step 4: Transfer funds to fine-tuning provider
    print("\nStep 4: Transferring funds to provider...")
    try:
        from zerog_py_sdk.utils import og_to_wei

        amount_wei = og_to_wei(TRANSFER_AMOUNT)
        broker.ledger.transfer_fund(
            PROVIDER_ADDRESS, "fine-tuning-v1.1", amount_wei
        )
        print(f"  Transferred {TRANSFER_AMOUNT} A0GI to provider")
    except Exception as e:
        print(f"  Transfer note: {e}")
        print("  (May already have sufficient balance with provider)")

    # Step 5: Acknowledge provider TEE signer
    print("\nStep 5: Acknowledging provider TEE signer...")
    result = broker.fine_tuning.acknowledge_provider_signer(PROVIDER_ADDRESS)
    print(f"  Result: {result}")

    # Step 6: Upload dataset to TEE
    print("\nStep 6: Uploading dataset to TEE...")
    upload_result = broker.fine_tuning._provider.upload_dataset_to_tee(
        PROVIDER_ADDRESS, DATASET_PATH
    )
    dataset_hash = upload_result["datasetHash"]
    print(f"  Dataset hash: {dataset_hash}")

    # Step 7: Create fine-tuning task
    print("\nStep 7: Creating fine-tuning task...")
    task_id = broker.fine_tuning.create_task(
        provider_address=PROVIDER_ADDRESS,
        pre_trained_model_name=MODEL_NAME,
        dataset_hash=dataset_hash,
        training_path=TRAINING_PARAMS_PATH,
    )
    print(f"  Task ID: {task_id}")

    # Step 8: Monitor training progress
    # Typical states: Init -> Training -> Trained (or Failed/Cancelled)
    print("\nStep 8: Monitoring training progress...")
    start_time = time.time()
    last_progress = None
    while True:
        time.sleep(15)
        elapsed = int(time.time() - start_time)
        try:
            task = broker.fine_tuning.get_task(PROVIDER_ADDRESS, task_id)
            if task.progress != last_progress:
                print(f"  [{elapsed}s] Progress: {task.progress}")
                last_progress = task.progress

            if task.progress in ("Trained", "Delivered", "Completed", "Failed", "Cancelled"):
                break
        except Exception:
            # Provider may be unreachable while GPU is busy training
            print(f"  [{elapsed}s] Provider busy (training in progress), retrying...")

    total = int(time.time() - start_time)
    print(f"  Training finished in {total}s with status: {last_progress}")

    # Step 9: Get training logs
    print("\nStep 9: Fetching training logs (last 1000 chars)...")
    try:
        log = broker.fine_tuning.get_log(PROVIDER_ADDRESS, task_id)
        print(log[-1000:] if len(log) > 1000 else log)
    except Exception as e:
        print(f"  Could not fetch logs: {e}")

    # Step 10: Acknowledge the delivered model on-chain
    # IMPORTANT: You must acknowledge the deliverable before you can create new tasks.
    # The provider will reject new tasks if a previous deliverable is unacknowledged.
    # This step downloads the LoRA weights, verifies the hash, then acknowledges on-chain.
    if last_progress in ("Trained", "Delivered"):
        print("\nStep 10: Acknowledging delivered model on-chain...")

        # Wait for the provider to transition from Trained -> Delivered
        for _ in range(10):
            task = broker.fine_tuning.get_task(PROVIDER_ADDRESS, task_id)
            if task.progress == "Delivered":
                break
            print(f"  Waiting for delivery (current: {task.progress})...")
            time.sleep(10)

        # Download LoRA weights and acknowledge on-chain
        output_path = os.path.join(SCRIPT_DIR, f"lora_{task_id}.bin")
        try:
            result = broker.fine_tuning.acknowledge_model(
                PROVIDER_ADDRESS, task_id, data_path=output_path
            )
            print(f"  LoRA weights downloaded to: {output_path}")
            print(f"  Model acknowledged on-chain: {result}")
        except Exception as e:
            print(f"  Acknowledge error: {e}")
            print("  You can acknowledge later with:")
            print(f'    broker.fine_tuning.acknowledge_model("{PROVIDER_ADDRESS}", "{task_id}", "output.bin")')

    print("\nDone!")


if __name__ == "__main__":
    main()
