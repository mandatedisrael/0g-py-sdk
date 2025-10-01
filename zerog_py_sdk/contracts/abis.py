"""
Smart contract ABIs for the 0G Compute Network.

This module contains the Application Binary Interface (ABI) definitions
for interacting with 0G smart contracts.
"""

# Contract Addresses on Testnet
LEDGER_ADDRESS = "0x907a552804CECC0cBAeCf734E2B9E45b2FA6a960"
INFERENCE_SERVING_ADDRESS = "0x192ff84e5E3Ef3A6D29F508a56bF9beb344471f3"
FINETUNING_SERVING_ADDRESS = "0x9472Cc442354a5a3bEeA5755Ec781937aB891c10"
AUTOMATA_CONTRACT_ADDRESS = "0xE26E11B257856B0bEBc4C759aaBDdea72B64351F"

# Default contract address for the broker (InferenceServing)
DEFAULT_CONTRACT_ADDRESS = INFERENCE_SERVING_ADDRESS

# ABI for the 0G Serving Contract
SERVING_CONTRACT_ABI = [
    {
        "inputs": [
            {"internalType": "address", "name": "user", "type": "address"},
            {"internalType": "address", "name": "provider", "type": "address"}
        ],
        "name": "AccountExists",
        "type": "error"
    },
    {
        "inputs": [
            {"internalType": "address", "name": "user", "type": "address"},
            {"internalType": "address", "name": "provider", "type": "address"}
        ],
        "name": "AccountNotExists",
        "type": "error"
    },
    {
        "inputs": [{"internalType": "string", "name": "reason", "type": "string"}],
        "name": "InvalidProofInputs",
        "type": "error"
    },
    {
        "inputs": [{"internalType": "string", "name": "reason", "type": "string"}],
        "name": "InvalidTEESignature",
        "type": "error"
    },
    {
        "inputs": [{"internalType": "address", "name": "provider", "type": "address"}],
        "name": "ServiceNotExist",
        "type": "error"
    },
    {
        "inputs": [
            {"internalType": "address", "name": "user", "type": "address"},
            {"internalType": "address", "name": "provider", "type": "address"}
        ],
        "name": "TooManyRefunds",
        "type": "error"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "address", "name": "user", "type": "address"},
            {"indexed": True, "internalType": "address", "name": "provider", "type": "address"},
            {"indexed": False, "internalType": "uint256", "name": "amount", "type": "uint256"},
            {"indexed": False, "internalType": "uint256", "name": "pendingRefund", "type": "uint256"}
        ],
        "name": "BalanceUpdated",
        "type": "event"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "address", "name": "previousOwner", "type": "address"},
            {"indexed": True, "internalType": "address", "name": "newOwner", "type": "address"}
        ],
        "name": "OwnershipTransferred",
        "type": "event"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "address", "name": "user", "type": "address"},
            {"indexed": True, "internalType": "address", "name": "provider", "type": "address"},
            {"indexed": True, "internalType": "uint256", "name": "index", "type": "uint256"},
            {"indexed": False, "internalType": "uint256", "name": "timestamp", "type": "uint256"}
        ],
        "name": "RefundRequested",
        "type": "event"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "address", "name": "service", "type": "address"}
        ],
        "name": "ServiceRemoved",
        "type": "event"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "address", "name": "service", "type": "address"},
            {"indexed": False, "internalType": "string", "name": "serviceType", "type": "string"},
            {"indexed": False, "internalType": "string", "name": "url", "type": "string"},
            {"indexed": False, "internalType": "uint256", "name": "inputPrice", "type": "uint256"},
            {"indexed": False, "internalType": "uint256", "name": "outputPrice", "type": "uint256"},
            {"indexed": False, "internalType": "uint256", "name": "updatedAt", "type": "uint256"},
            {"indexed": False, "internalType": "string", "name": "model", "type": "string"},
            {"indexed": False, "internalType": "string", "name": "verifiability", "type": "string"}
        ],
        "name": "ServiceUpdated",
        "type": "event"
    },
    {
        "inputs": [
            {"internalType": "address", "name": "user", "type": "address"},
            {"internalType": "address", "name": "provider", "type": "address"}
        ],
        "name": "accountExists",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "address", "name": "provider", "type": "address"},
            {"internalType": "uint256[2]", "name": "providerPubKey", "type": "uint256[2]"}
        ],
        "name": "acknowledgeProviderSigner",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "address", "name": "provider", "type": "address"},
            {"internalType": "address", "name": "teeSignerAddress", "type": "address"}
        ],
        "name": "acknowledgeTEESigner",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "address", "name": "user", "type": "address"},
            {"internalType": "address", "name": "provider", "type": "address"},
            {"internalType": "uint256[2]", "name": "signer", "type": "uint256[2]"},
            {"internalType": "string", "name": "additionalInfo", "type": "string"}
        ],
        "name": "addAccount",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "address", "name": "user", "type": "address"},
            {"internalType": "address", "name": "provider", "type": "address"},
            {"internalType": "uint256", "name": "cancelRetrievingAmount", "type": "uint256"}
        ],
        "name": "depositFund",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "address", "name": "user", "type": "address"},
            {"internalType": "address", "name": "provider", "type": "address"}
        ],
        "name": "getAccount",
        "outputs": [
            {
                "components": [
                    {"internalType": "address", "name": "user", "type": "address"},
                    {"internalType": "address", "name": "provider", "type": "address"},
                    {"internalType": "uint256", "name": "nonce", "type": "uint256"},
                    {"internalType": "uint256", "name": "balance", "type": "uint256"},
                    {"internalType": "uint256", "name": "pendingRefund", "type": "uint256"},
                    {"internalType": "uint256[2]", "name": "signer", "type": "uint256[2]"},
                    {
                        "components": [
                            {"internalType": "uint256", "name": "index", "type": "uint256"},
                            {"internalType": "uint256", "name": "amount", "type": "uint256"},
                            {"internalType": "uint256", "name": "createdAt", "type": "uint256"},
                            {"internalType": "bool", "name": "processed", "type": "bool"}
                        ],
                        "internalType": "struct Refund[]",
                        "name": "refunds",
                        "type": "tuple[]"
                    },
                    {"internalType": "string", "name": "additionalInfo", "type": "string"},
                    {"internalType": "uint256[2]", "name": "providerPubKey", "type": "uint256[2]"},
                    {"internalType": "address", "name": "teeSignerAddress", "type": "address"},
                    {"internalType": "uint256", "name": "validRefundsLength", "type": "uint256"}
                ],
                "internalType": "struct Account",
                "name": "",
                "type": "tuple"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "getAllServices",
        "outputs": [
            {
                "components": [
                    {"internalType": "address", "name": "provider", "type": "address"},
                    {"internalType": "string", "name": "serviceType", "type": "string"},
                    {"internalType": "string", "name": "url", "type": "string"},
                    {"internalType": "uint256", "name": "inputPrice", "type": "uint256"},
                    {"internalType": "uint256", "name": "outputPrice", "type": "uint256"},
                    {"internalType": "uint256", "name": "updatedAt", "type": "uint256"},
                    {"internalType": "string", "name": "model", "type": "string"},
                    {"internalType": "string", "name": "verifiability", "type": "string"},
                    {"internalType": "string", "name": "additionalInfo", "type": "string"}
                ],
                "internalType": "struct Service[]",
                "name": "services",
                "type": "tuple[]"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "address", "name": "provider", "type": "address"}],
        "name": "getService",
        "outputs": [
            {
                "components": [
                    {"internalType": "address", "name": "provider", "type": "address"},
                    {"internalType": "string", "name": "serviceType", "type": "string"},
                    {"internalType": "string", "name": "url", "type": "string"},
                    {"internalType": "uint256", "name": "inputPrice", "type": "uint256"},
                    {"internalType": "uint256", "name": "outputPrice", "type": "uint256"},
                    {"internalType": "uint256", "name": "updatedAt", "type": "uint256"},
                    {"internalType": "string", "name": "model", "type": "string"},
                    {"internalType": "string", "name": "verifiability", "type": "string"},
                    {"internalType": "string", "name": "additionalInfo", "type": "string"}
                ],
                "internalType": "struct Service",
                "name": "service",
                "type": "tuple"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "address", "name": "user", "type": "address"},
            {"internalType": "address", "name": "provider", "type": "address"}
        ],
        "name": "requestRefundAll",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]