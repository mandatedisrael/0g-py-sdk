"""
Smart contract ABIs for the 0G Compute Network.

This module contains the Application Binary Interface (ABI) definitions
for interacting with 0G smart contracts.
"""

from ..constants import (
    CONTRACT_ADDRESSES,
    AUTOMATA_CONTRACT_ADDRESS,
    DEFAULT_LEDGER_ADDRESS,
    DEFAULT_SERVING_ADDRESS,
    DEFAULT_FINETUNING_ADDRESS,
)

# Re-export for backward compatibility
__all__ = [
    "CONTRACT_ADDRESSES",
    "AUTOMATA_CONTRACT_ADDRESS", 
    "DEFAULT_LEDGER_ADDRESS",
    "DEFAULT_SERVING_ADDRESS",
    "DEFAULT_FINETUNING_ADDRESS",
    "LEDGER_CONTRACT_ABI",
    "SERVING_CONTRACT_ABI",
]

# Legacy aliases (deprecated - use constants module directly)
LEDGER_ADDRESS = DEFAULT_LEDGER_ADDRESS
INFERENCE_SERVING_ADDRESS = DEFAULT_SERVING_ADDRESS
FINETUNING_SERVING_ADDRESS = DEFAULT_FINETUNING_ADDRESS

# ABI for the LedgerManager Contract
LEDGER_CONTRACT_ABI = [
    {"inputs": [{"internalType": "address", "name": "user", "type": "address"}], "name": "InsufficientBalance", "type": "error"},
    {"inputs": [{"internalType": "string", "name": "serviceType", "type": "string"}], "name": "InvalidServiceType", "type": "error"},
    {"inputs": [{"internalType": "address", "name": "user", "type": "address"}], "name": "LedgerExists", "type": "error"},
    {"inputs": [{"internalType": "address", "name": "user", "type": "address"}], "name": "LedgerNotExists", "type": "error"},
    {"inputs": [{"internalType": "uint256", "name": "requested", "type": "uint256"}, {"internalType": "uint256", "name": "maximum", "type": "uint256"}], "name": "TooManyProviders", "type": "error"},
    {"anonymous": False, "inputs": [{"indexed": True, "internalType": "address", "name": "previousOwner", "type": "address"}, {"indexed": True, "internalType": "address", "name": "newOwner", "type": "address"}], "name": "OwnershipTransferred", "type": "event"},
    {"inputs": [], "name": "MAX_PROVIDERS_PER_BATCH", "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
    # Updated addLedger - now takes just additionalInfo string
    {"inputs": [{"internalType": "string", "name": "additionalInfo", "type": "string"}], "name": "addLedger", "outputs": [], "stateMutability": "payable", "type": "function"},
    {"inputs": [], "name": "deleteLedger", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [], "name": "depositFund", "outputs": [], "stateMutability": "payable", "type": "function"},
    {"inputs": [{"internalType": "address", "name": "recipient", "type": "address"}], "name": "depositFundFor", "outputs": [], "stateMutability": "payable", "type": "function"},
    {"inputs": [], "name": "fineTuningAddress", "outputs": [{"internalType": "address payable", "name": "", "type": "address"}], "stateMutability": "view", "type": "function"},
    # Updated getAllLedgers with new Ledger struct
    {"inputs": [{"internalType": "uint256", "name": "offset", "type": "uint256"}, {"internalType": "uint256", "name": "limit", "type": "uint256"}], "name": "getAllLedgers", "outputs": [{"components": [{"internalType": "address", "name": "user", "type": "address"}, {"internalType": "uint256", "name": "availableBalance", "type": "uint256"}, {"internalType": "uint256", "name": "totalBalance", "type": "uint256"}, {"internalType": "string", "name": "additionalInfo", "type": "string"}], "internalType": "struct Ledger[]", "name": "ledgers", "type": "tuple[]"}, {"internalType": "uint256", "name": "total", "type": "uint256"}], "stateMutability": "view", "type": "function"},
    # Updated getLedger with new Ledger struct (user, availableBalance, totalBalance, additionalInfo)
    {"inputs": [{"internalType": "address", "name": "user", "type": "address"}], "name": "getLedger", "outputs": [{"components": [{"internalType": "address", "name": "user", "type": "address"}, {"internalType": "uint256", "name": "availableBalance", "type": "uint256"}, {"internalType": "uint256", "name": "totalBalance", "type": "uint256"}, {"internalType": "string", "name": "additionalInfo", "type": "string"}], "internalType": "struct Ledger", "name": "", "type": "tuple"}], "stateMutability": "view", "type": "function"},
    # getLedgerProviders for getting provider lists
    {"inputs": [{"internalType": "address", "name": "user", "type": "address"}, {"internalType": "string", "name": "serviceType", "type": "string"}], "name": "getLedgerProviders", "outputs": [{"internalType": "address[]", "name": "", "type": "address[]"}], "stateMutability": "view", "type": "function"},
    # getServiceInfo - returns service registration details for a contract address
    {"inputs": [{"internalType": "address", "name": "serviceAddress", "type": "address"}], "name": "getServiceInfo", "outputs": [{"components": [{"internalType": "address", "name": "serviceAddress", "type": "address"}, {"internalType": "contract IServing", "name": "serviceContract", "type": "address"}, {"internalType": "string", "name": "serviceType", "type": "string"}, {"internalType": "string", "name": "version", "type": "string"}, {"internalType": "string", "name": "fullName", "type": "string"}, {"internalType": "string", "name": "description", "type": "string"}, {"internalType": "uint256", "name": "serviceId", "type": "uint256"}, {"internalType": "uint256", "name": "registeredAt", "type": "uint256"}], "internalType": "struct ServiceInfo", "name": "", "type": "tuple"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "inferenceAddress", "outputs": [{"internalType": "address payable", "name": "", "type": "address"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"internalType": "address", "name": "_inferenceAddress", "type": "address"}, {"internalType": "address", "name": "_fineTuningAddress", "type": "address"}, {"internalType": "address", "name": "owner", "type": "address"}], "name": "initialize", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [], "name": "initialized", "outputs": [{"internalType": "bool", "name": "", "type": "bool"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "owner", "outputs": [{"internalType": "address", "name": "", "type": "address"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"internalType": "uint256", "name": "amount", "type": "uint256"}], "name": "refund", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [], "name": "renounceOwnership", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"internalType": "address[]", "name": "providers", "type": "address[]"}, {"internalType": "string", "name": "serviceType", "type": "string"}], "name": "retrieveFund", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"internalType": "address", "name": "user", "type": "address"}, {"internalType": "uint256", "name": "amount", "type": "uint256"}], "name": "spendFund", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"internalType": "address", "name": "provider", "type": "address"}, {"internalType": "string", "name": "serviceTypeStr", "type": "string"}, {"internalType": "uint256", "name": "amount", "type": "uint256"}], "name": "transferFund", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"internalType": "address", "name": "newOwner", "type": "address"}], "name": "transferOwnership", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"stateMutability": "payable", "type": "receive"}
]

# ABI for the InferenceServing Contract
# Updated to match official 0g-serving-broker (March 2026)
SERVING_CONTRACT_ABI = [
    # Errors
    {"inputs": [{"internalType": "address", "name": "user", "type": "address"}, {"internalType": "address", "name": "provider", "type": "address"}], "name": "AccountExists", "type": "error"},
    {"inputs": [{"internalType": "address", "name": "user", "type": "address"}, {"internalType": "address", "name": "provider", "type": "address"}], "name": "AccountNotExists", "type": "error"},
    {"inputs": [{"internalType": "string", "name": "reason", "type": "string"}], "name": "InvalidProofInputs", "type": "error"},
    {"inputs": [{"internalType": "string", "name": "reason", "type": "string"}], "name": "InvalidTEESignature", "type": "error"},
    {"inputs": [{"internalType": "address", "name": "provider", "type": "address"}], "name": "ServiceNotExist", "type": "error"},
    {"inputs": [{"internalType": "address", "name": "user", "type": "address"}, {"internalType": "address", "name": "provider", "type": "address"}], "name": "TooManyRefunds", "type": "error"},
    # Events
    {"anonymous": False, "inputs": [{"indexed": True, "internalType": "address", "name": "user", "type": "address"}, {"indexed": True, "internalType": "address", "name": "provider", "type": "address"}, {"indexed": False, "internalType": "uint256", "name": "amount", "type": "uint256"}, {"indexed": False, "internalType": "uint256", "name": "pendingRefund", "type": "uint256"}], "name": "BalanceUpdated", "type": "event"},
    {"anonymous": False, "inputs": [{"indexed": True, "internalType": "address", "name": "previousOwner", "type": "address"}, {"indexed": True, "internalType": "address", "name": "newOwner", "type": "address"}], "name": "OwnershipTransferred", "type": "event"},
    {"anonymous": False, "inputs": [{"indexed": True, "internalType": "address", "name": "user", "type": "address"}, {"indexed": True, "internalType": "address", "name": "provider", "type": "address"}, {"indexed": True, "internalType": "uint256", "name": "index", "type": "uint256"}, {"indexed": False, "internalType": "uint256", "name": "timestamp", "type": "uint256"}], "name": "RefundRequested", "type": "event"},
    {"anonymous": False, "inputs": [{"indexed": True, "internalType": "address", "name": "service", "type": "address"}], "name": "ServiceRemoved", "type": "event"},
    {"anonymous": False, "inputs": [{"indexed": True, "internalType": "address", "name": "service", "type": "address"}, {"indexed": False, "internalType": "string", "name": "serviceType", "type": "string"}, {"indexed": False, "internalType": "string", "name": "url", "type": "string"}, {"indexed": False, "internalType": "uint256", "name": "inputPrice", "type": "uint256"}, {"indexed": False, "internalType": "uint256", "name": "outputPrice", "type": "uint256"}, {"indexed": False, "internalType": "uint256", "name": "updatedAt", "type": "uint256"}, {"indexed": False, "internalType": "string", "name": "model", "type": "string"}, {"indexed": False, "internalType": "string", "name": "verifiability", "type": "string"}], "name": "ServiceUpdated", "type": "event"},
    # Functions
    {"inputs": [{"internalType": "address", "name": "user", "type": "address"}, {"internalType": "address", "name": "provider", "type": "address"}], "name": "accountExists", "outputs": [{"internalType": "bool", "name": "", "type": "bool"}], "stateMutability": "view", "type": "function"},
    # Updated: acknowledgeTEESigner now takes (provider, bool) not (provider, address)
    {"inputs": [{"internalType": "address", "name": "provider", "type": "address"}, {"internalType": "bool", "name": "acknowledged", "type": "bool"}], "name": "acknowledgeTEESigner", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    # Updated: addAccount no longer takes signer uint256[2]
    {"inputs": [{"internalType": "address", "name": "user", "type": "address"}, {"internalType": "address", "name": "provider", "type": "address"}, {"internalType": "string", "name": "additionalInfo", "type": "string"}], "name": "addAccount", "outputs": [], "stateMutability": "payable", "type": "function"},
    # Updated: ServiceParams now includes teeSignerAddress
    {"inputs": [{"components": [{"internalType": "string", "name": "serviceType", "type": "string"}, {"internalType": "string", "name": "url", "type": "string"}, {"internalType": "string", "name": "model", "type": "string"}, {"internalType": "string", "name": "verifiability", "type": "string"}, {"internalType": "uint256", "name": "inputPrice", "type": "uint256"}, {"internalType": "uint256", "name": "outputPrice", "type": "uint256"}, {"internalType": "string", "name": "additionalInfo", "type": "string"}, {"internalType": "address", "name": "teeSignerAddress", "type": "address"}], "internalType": "struct ServiceParams", "name": "params", "type": "tuple"}], "name": "addOrUpdateService", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"internalType": "address", "name": "user", "type": "address"}, {"internalType": "address", "name": "provider", "type": "address"}], "name": "deleteAccount", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"internalType": "address", "name": "user", "type": "address"}, {"internalType": "address", "name": "provider", "type": "address"}, {"internalType": "uint256", "name": "cancelRetrievingAmount", "type": "uint256"}], "name": "depositFund", "outputs": [], "stateMutability": "payable", "type": "function"},
    # Updated: Account struct - removed signer/providerPubKey/teeSignerAddress, added acknowledged/generation/revokedBitmap
    {"inputs": [{"internalType": "address", "name": "user", "type": "address"}, {"internalType": "address", "name": "provider", "type": "address"}], "name": "getAccount", "outputs": [{"components": [{"internalType": "address", "name": "user", "type": "address"}, {"internalType": "address", "name": "provider", "type": "address"}, {"internalType": "uint256", "name": "nonce", "type": "uint256"}, {"internalType": "uint256", "name": "balance", "type": "uint256"}, {"internalType": "uint256", "name": "pendingRefund", "type": "uint256"}, {"components": [{"internalType": "uint256", "name": "index", "type": "uint256"}, {"internalType": "uint256", "name": "amount", "type": "uint256"}, {"internalType": "uint256", "name": "createdAt", "type": "uint256"}, {"internalType": "bool", "name": "processed", "type": "bool"}], "internalType": "struct Refund[]", "name": "refunds", "type": "tuple[]"}, {"internalType": "string", "name": "additionalInfo", "type": "string"}, {"internalType": "bool", "name": "acknowledged", "type": "bool"}, {"internalType": "uint256", "name": "validRefundsLength", "type": "uint256"}, {"internalType": "uint256", "name": "generation", "type": "uint256"}, {"internalType": "uint256", "name": "revokedBitmap", "type": "uint256"}], "internalType": "struct Account", "name": "", "type": "tuple"}], "stateMutability": "view", "type": "function"},
    # Paginated getAllServices with updated Service struct including teeSignerAddress
    {"inputs": [{"internalType": "uint256", "name": "offset", "type": "uint256"}, {"internalType": "uint256", "name": "limit", "type": "uint256"}], "name": "getAllServices", "outputs": [{"components": [{"internalType": "address", "name": "provider", "type": "address"}, {"internalType": "string", "name": "serviceType", "type": "string"}, {"internalType": "string", "name": "url", "type": "string"}, {"internalType": "uint256", "name": "inputPrice", "type": "uint256"}, {"internalType": "uint256", "name": "outputPrice", "type": "uint256"}, {"internalType": "uint256", "name": "updatedAt", "type": "uint256"}, {"internalType": "string", "name": "model", "type": "string"}, {"internalType": "string", "name": "verifiability", "type": "string"}, {"internalType": "string", "name": "additionalInfo", "type": "string"}, {"internalType": "address", "name": "teeSignerAddress", "type": "address"}, {"internalType": "bool", "name": "teeSignerAcknowledged", "type": "bool"}], "internalType": "struct Service[]", "name": "services", "type": "tuple[]"}, {"internalType": "uint256", "name": "total", "type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"internalType": "address", "name": "provider", "type": "address"}], "name": "getService", "outputs": [{"components": [{"internalType": "address", "name": "provider", "type": "address"}, {"internalType": "string", "name": "serviceType", "type": "string"}, {"internalType": "string", "name": "url", "type": "string"}, {"internalType": "uint256", "name": "inputPrice", "type": "uint256"}, {"internalType": "uint256", "name": "outputPrice", "type": "uint256"}, {"internalType": "uint256", "name": "updatedAt", "type": "uint256"}, {"internalType": "string", "name": "model", "type": "string"}, {"internalType": "string", "name": "verifiability", "type": "string"}, {"internalType": "string", "name": "additionalInfo", "type": "string"}], "internalType": "struct Service", "name": "service", "type": "tuple"}], "stateMutability": "view", "type": "function"},
    # New query functions
    {"inputs": [{"internalType": "address", "name": "provider", "type": "address"}], "name": "serviceExists", "outputs": [{"internalType": "bool", "name": "", "type": "bool"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"internalType": "address", "name": "user", "type": "address"}, {"internalType": "address", "name": "provider", "type": "address"}, {"internalType": "uint8", "name": "tokenId", "type": "uint8"}], "name": "isTokenRevoked", "outputs": [{"internalType": "bool", "name": "", "type": "bool"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"internalType": "address", "name": "user", "type": "address"}, {"internalType": "address", "name": "provider", "type": "address"}], "name": "getPendingRefund", "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
    # Token and refund management
    {"inputs": [{"internalType": "address", "name": "provider", "type": "address"}, {"internalType": "uint8", "name": "tokenId", "type": "uint8"}], "name": "revokeToken", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"internalType": "address", "name": "provider", "type": "address"}, {"internalType": "uint8[]", "name": "tokenIds", "type": "uint8[]"}], "name": "revokeTokens", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"internalType": "address", "name": "provider", "type": "address"}], "name": "revokeAllTokens", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"internalType": "address", "name": "user", "type": "address"}, {"internalType": "address", "name": "provider", "type": "address"}], "name": "requestRefundAll", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"internalType": "address", "name": "user", "type": "address"}, {"internalType": "address", "name": "provider", "type": "address"}], "name": "processRefund", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [], "name": "removeService", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"internalType": "address", "name": "provider", "type": "address"}], "name": "revokeTEESignerAcknowledgement", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    # Admin/config
    {"inputs": [], "name": "lockTime", "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "ledgerAddress", "outputs": [{"internalType": "address", "name": "", "type": "address"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "owner", "outputs": [{"internalType": "address", "name": "", "type": "address"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"internalType": "address", "name": "newOwner", "type": "address"}], "name": "transferOwnership", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
]