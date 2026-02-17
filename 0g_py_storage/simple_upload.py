#!/usr/bin/env python3
"""
Minimal upload script for 0G Storage (Testnet).

Usage:
    export OG_PRIVATE_KEY="your_private_key"
    python3 simple_upload.py <file_path>

Get testnet tokens: https://faucet.0g.ai
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.file import ZgFile
from core.indexer import Indexer
from web3 import Web3
from eth_account import Account

# Testnet Config
INDEXER_URL = "https://indexer-storage-testnet-turbo.0g.ai"
BLOCKCHAIN_RPC = "https://evmrpc-testnet.0g.ai"


def upload(file_path: str):
    # Load private key from env or .env file
    private_key = os.environ.get("OG_PRIVATE_KEY") or os.environ.get("PRIVATE_KEY")
    if not private_key:
        # Try loading from .env file
        env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    if line.startswith("PRIVATE_KEY="):
                        private_key = line.strip().split("=", 1)[1].strip('"').strip("'")
                        break
    
    if not private_key:
        print("Error: Set PRIVATE_KEY in .env or OG_PRIVATE_KEY env variable")
        print("Get testnet tokens at: https://faucet.0g.ai")
        return None

    # Load file
    print(f"Loading file: {file_path}")
    file = ZgFile.from_file_path(file_path)
    tree, err = file.merkle_tree()
    if err:
        print(f"Error: {err}")
        return None

    root_hash = tree.root_hash()
    print(f"Root hash: {root_hash}")

    # Setup
    account = Account.from_key(private_key)
    print(f"Account: {account.address}")

    # Check balance
    web3 = Web3(Web3.HTTPProvider(BLOCKCHAIN_RPC))
    balance = web3.eth.get_balance(account.address)
    print(f"Balance: {web3.from_wei(balance, 'ether')} 0G")
    
    if balance == 0:
        print("Error: No balance. Get tokens at https://faucet.0g.ai")
        return None

    indexer = Indexer(INDEXER_URL)
    uploader, err = indexer.new_uploader_from_indexer_nodes(
        BLOCKCHAIN_RPC, 
        account,
        expected_replica=1
    )
    if err:
        print(f"Error creating uploader: {err}")
        return None

    # Upload
    print("Uploading...")
    result, err = uploader.upload_file(file, {"tags": b"\x00", "account": account})
    if err:
        print(f"Upload error: {err}")
        return None

    print(f"\nSuccess!")
    print(f"TX Hash: {result.get('txHash')}")
    print(f"Root Hash: {result.get('rootHash')}")
    return result.get("rootHash")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 simple_upload.py <file_path>")
        print("\nExample:")
        print("  export OG_PRIVATE_KEY='0x...'")
        print("  python3 simple_upload.py test.txt")
        sys.exit(1)

    result = upload(sys.argv[1])
    sys.exit(0 if result else 1)
