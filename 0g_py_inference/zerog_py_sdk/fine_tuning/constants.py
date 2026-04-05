TESTNET_CHAIN_ID = 16602
MAINNET_CHAIN_ID = 16661
HARDHAT_CHAIN_ID = 31337

# Storage endpoints
ZG_RPC_ENDPOINT_TESTNET = "https://evmrpc-testnet.0g.ai"
ZG_RPC_ENDPOINT_MAINNET = "https://evmrpc.0g.ai"

INDEXER_URL_TESTNET_STANDARD = "https://indexer-storage-testnet-standard.0g.ai"
INDEXER_URL_TESTNET_TURBO = "https://indexer-storage-testnet-turbo.0g.ai"
INDEXER_URL_MAINNET_STANDARD = "https://indexer-storage-standard.0g.ai"
INDEXER_URL_MAINNET_TURBO = "https://indexer-storage-turbo.0g.ai"

# Token counter
TOKEN_COUNTER_MERKLE_ROOT = "0x4e8ae3790920b9971397f088fcfacbb9dad0c28ec2831f37f3481933b1fdbdbc"
TOKEN_COUNTER_FILE_HASH = "26ab266a12c9ce34611aba3f82baf056dc683181236d5fa15edb8eb8c8db3872"

# Model configurations per network
TESTNET_MODELS = {
    "Qwen2.5-0.5B-Instruct": {
        "turbo": "0xb4f76a886b8655c92bb021922d60b5e4d9271a5c9da98b6cb10937a06c2c75a7",
        "standard": "",
        "tokenizer": "Qwen/Qwen2.5-0.5B-Instruct",
        "type": "text",
        "description": "Qwen2.5-0.5B-Instruct is a compact instruction-tuned language model optimized for LoRA fine-tuning.",
    },
}

MAINNET_MODELS = {
    "Qwen2.5-0.5B-Instruct": {
        "turbo": "0xb4f76a886b8655c92bb021922d60b5e4d9271a5c9da98b6cb10937a06c2c75a7",
        "standard": "",
        "tokenizer": "Qwen/Qwen2.5-0.5B-Instruct",
        "type": "text",
        "description": "Qwen2.5-0.5B-Instruct is a compact instruction-tuned language model optimized for LoRA fine-tuning.",
    },
    "Qwen3-32B": {
        "turbo": "0x2e6f9620c35bdcb2b753cc7aa34e78077a8ed133e36fa36008fd6bdfd29af3a5",
        "standard": "",
        "tokenizer": "Qwen/Qwen3-32B",
        "type": "text",
        "description": "Qwen3-32B is a powerful 32B parameter language model with thinking/non-thinking mode switching. Optimized for LoRA fine-tuning.",
    },
}

HARDHAT_MODELS = {
    "mock-model": {
        "turbo": "0xcb42b5ca9e998c82dd239ef2d20d22a4ae16b3dc0ce0a855c93b52c7c2bab6dc",
        "standard": "",
        "tokenizer": "0x382842561e59d71f90c1861041989428dd2c1f664e65a56ea21f3ade216b2046",
        "type": "text",
        "description": "Mock model for local development and testing",
    },
}

# Legacy alias
MODEL_HASH_MAP = {**MAINNET_MODELS}


def get_model_config(chain_id: int) -> dict:
    if chain_id == MAINNET_CHAIN_ID:
        return MAINNET_MODELS
    elif chain_id == HARDHAT_CHAIN_ID:
        return HARDHAT_MODELS
    return TESTNET_MODELS


def get_storage_config(chain_id: int) -> dict:
    if chain_id == MAINNET_CHAIN_ID:
        return {
            "rpc_url": ZG_RPC_ENDPOINT_MAINNET,
            "indexer_url": INDEXER_URL_MAINNET_TURBO,
        }
    return {
        "rpc_url": ZG_RPC_ENDPOINT_TESTNET,
        "indexer_url": INDEXER_URL_TESTNET_TURBO,
    }
