FINE_TUNING_SERVING_ABI = [
    {
        "inputs": [
            {"internalType": "address", "name": "user", "type": "address"},
            {"internalType": "address", "name": "provider", "type": "address"},
        ],
        "name": "AccountExists",
        "type": "error",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "user", "type": "address"},
            {"internalType": "address", "name": "provider", "type": "address"},
        ],
        "name": "AccountNotExists",
        "type": "error",
    },
    {"inputs": [], "name": "AdditionalInfoTooLong", "type": "error"},
    {"inputs": [], "name": "AlreadyInitialized", "type": "error"},
    {
        "inputs": [
            {"internalType": "uint256", "name": "size", "type": "uint256"},
            {"internalType": "uint256", "name": "maxSize", "type": "uint256"},
        ],
        "name": "BatchSizeTooLarge",
        "type": "error",
    },
    {"inputs": [], "name": "CallerNotLedger", "type": "error"},
    {
        "inputs": [{"internalType": "string", "name": "id", "type": "string"}],
        "name": "CannotAcknowledgeSettledDeliverable",
        "type": "error",
    },
    {"inputs": [], "name": "CannotAddStakeWhenUpdating", "type": "error"},
    {
        "inputs": [{"internalType": "string", "name": "id", "type": "string"}],
        "name": "CannotEvictUnsettledDeliverable",
        "type": "error",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "user", "type": "address"},
            {"internalType": "address", "name": "provider", "type": "address"},
            {"internalType": "uint256", "name": "balance", "type": "uint256"},
        ],
        "name": "CannotRevokeWithNonZeroBalance",
        "type": "error",
    },
    {
        "inputs": [{"internalType": "string", "name": "id", "type": "string"}],
        "name": "DeliverableAlreadyExists",
        "type": "error",
    },
    {
        "inputs": [{"internalType": "string", "name": "id", "type": "string"}],
        "name": "DeliverableAlreadySettled",
        "type": "error",
    },
    {
        "inputs": [{"internalType": "uint256", "name": "length", "type": "uint256"}],
        "name": "DeliverableIdInvalidLength",
        "type": "error",
    },
    {
        "inputs": [{"internalType": "string", "name": "id", "type": "string"}],
        "name": "DeliverableNotExists",
        "type": "error",
    },
    {"inputs": [], "name": "DirectDepositsDisabled", "type": "error"},
    {"inputs": [], "name": "ETHTransferFailed", "type": "error"},
    {
        "inputs": [
            {"internalType": "uint256", "name": "provided", "type": "uint256"},
            {"internalType": "uint256", "name": "required", "type": "uint256"},
        ],
        "name": "InsufficientStake",
        "type": "error",
    },
    {"inputs": [], "name": "InvalidLedgerAddress", "type": "error"},
    {
        "inputs": [{"internalType": "string", "name": "reason", "type": "string"}],
        "name": "InvalidVerifierInput",
        "type": "error",
    },
    {
        "inputs": [{"internalType": "uint256", "name": "limit", "type": "uint256"}],
        "name": "LimitTooLarge",
        "type": "error",
    },
    {
        "inputs": [{"internalType": "uint256", "name": "lockTime", "type": "uint256"}],
        "name": "LockTimeOutOfRange",
        "type": "error",
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "percentage", "type": "uint256"}
        ],
        "name": "PenaltyPercentageTooHigh",
        "type": "error",
    },
    {
        "inputs": [{"internalType": "string", "name": "id", "type": "string"}],
        "name": "PreviousDeliverableNotAcknowledged",
        "type": "error",
    },
    {"inputs": [], "name": "SecretShouldBeEmpty", "type": "error"},
    {"inputs": [], "name": "SecretShouldNotBeEmpty", "type": "error"},
    {
        "inputs": [
            {"internalType": "address", "name": "provider", "type": "address"}
        ],
        "name": "ServiceNotExist",
        "type": "error",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "user", "type": "address"},
            {"internalType": "address", "name": "provider", "type": "address"},
        ],
        "name": "TooManyRefunds",
        "type": "error",
    },
    {"inputs": [], "name": "TransferToLedgerFailed", "type": "error"},
    # Events
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "address", "name": "user", "type": "address"},
            {"indexed": True, "internalType": "address", "name": "provider", "type": "address"},
            {"indexed": False, "internalType": "uint256", "name": "refundedAmount", "type": "uint256"},
        ],
        "name": "AccountDeleted",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "address", "name": "user", "type": "address"},
            {"indexed": True, "internalType": "address", "name": "provider", "type": "address"},
            {"indexed": False, "internalType": "uint256", "name": "amount", "type": "uint256"},
            {"indexed": False, "internalType": "uint256", "name": "pendingRefund", "type": "uint256"},
        ],
        "name": "BalanceUpdated",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "address", "name": "user", "type": "address"},
            {"indexed": True, "internalType": "address", "name": "provider", "type": "address"},
            {"indexed": False, "internalType": "string", "name": "deliverableId", "type": "string"},
            {"indexed": False, "internalType": "uint256", "name": "timestamp", "type": "uint256"},
        ],
        "name": "DeliverableAcknowledged",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "address", "name": "user", "type": "address"},
            {"indexed": True, "internalType": "address", "name": "provider", "type": "address"},
            {"indexed": False, "internalType": "string", "name": "deliverableId", "type": "string"},
            {"indexed": False, "internalType": "bytes", "name": "modelRootHash", "type": "bytes"},
            {"indexed": False, "internalType": "uint256", "name": "timestamp", "type": "uint256"},
        ],
        "name": "DeliverableAdded",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "address", "name": "provider", "type": "address"},
            {"indexed": True, "internalType": "address", "name": "user", "type": "address"},
            {"indexed": False, "internalType": "string", "name": "evictedDeliverableId", "type": "string"},
            {"indexed": False, "internalType": "string", "name": "newDeliverableId", "type": "string"},
            {"indexed": False, "internalType": "uint256", "name": "timestamp", "type": "uint256"},
        ],
        "name": "DeliverableEvicted",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "address", "name": "user", "type": "address"},
            {"indexed": True, "internalType": "address", "name": "provider", "type": "address"},
            {"indexed": False, "internalType": "string", "name": "deliverableId", "type": "string"},
            {"indexed": False, "internalType": "uint256", "name": "fee", "type": "uint256"},
            {"indexed": False, "internalType": "bool", "name": "acknowledged", "type": "bool"},
            {"indexed": False, "internalType": "uint256", "name": "nonce", "type": "uint256"},
        ],
        "name": "FeesSettled",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": False, "internalType": "uint8", "name": "version", "type": "uint8"}
        ],
        "name": "Initialized",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": False, "internalType": "uint256", "name": "oldLockTime", "type": "uint256"},
            {"indexed": False, "internalType": "uint256", "name": "newLockTime", "type": "uint256"},
        ],
        "name": "LockTimeUpdated",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "address", "name": "previousOwner", "type": "address"},
            {"indexed": True, "internalType": "address", "name": "newOwner", "type": "address"},
        ],
        "name": "OwnershipTransferred",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "address", "name": "provider", "type": "address"},
            {"indexed": False, "internalType": "uint256", "name": "amount", "type": "uint256"},
        ],
        "name": "ProviderStakeReturned",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "address", "name": "provider", "type": "address"},
            {"indexed": False, "internalType": "uint256", "name": "amount", "type": "uint256"},
        ],
        "name": "ProviderStaked",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "address", "name": "provider", "type": "address"},
            {"indexed": True, "internalType": "address", "name": "teeSignerAddress", "type": "address"},
            {"indexed": False, "internalType": "bool", "name": "acknowledged", "type": "bool"},
        ],
        "name": "ProviderTEESignerAcknowledged",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "address", "name": "user", "type": "address"},
            {"indexed": True, "internalType": "address", "name": "provider", "type": "address"},
            {"indexed": True, "internalType": "uint256", "name": "index", "type": "uint256"},
            {"indexed": False, "internalType": "uint256", "name": "timestamp", "type": "uint256"},
        ],
        "name": "RefundRequested",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "address", "name": "provider", "type": "address"}
        ],
        "name": "ServiceRemoved",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "address", "name": "provider", "type": "address"},
            {"indexed": False, "internalType": "string", "name": "url", "type": "string"},
            {
                "components": [
                    {"internalType": "uint256", "name": "cpuCount", "type": "uint256"},
                    {"internalType": "uint256", "name": "nodeMemory", "type": "uint256"},
                    {"internalType": "uint256", "name": "gpuCount", "type": "uint256"},
                    {"internalType": "uint256", "name": "nodeStorage", "type": "uint256"},
                    {"internalType": "string", "name": "gpuType", "type": "string"},
                ],
                "indexed": False,
                "internalType": "struct Quota",
                "name": "quota",
                "type": "tuple",
            },
            {"indexed": False, "internalType": "uint256", "name": "pricePerToken", "type": "uint256"},
            {"indexed": False, "internalType": "address", "name": "teeSignerAddress", "type": "address"},
            {"indexed": False, "internalType": "bool", "name": "occupied", "type": "bool"},
        ],
        "name": "ServiceUpdated",
        "type": "event",
    },
    # Functions
    {
        "inputs": [],
        "name": "MAX_LOCKTIME",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "MIN_LOCKTIME",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "MIN_PROVIDER_STAKE",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "user", "type": "address"},
            {"internalType": "address", "name": "provider", "type": "address"},
        ],
        "name": "accountExists",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "provider", "type": "address"},
            {"internalType": "string", "name": "id", "type": "string"},
        ],
        "name": "acknowledgeDeliverable",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "provider", "type": "address"},
            {"internalType": "bool", "name": "acknowledged", "type": "bool"},
        ],
        "name": "acknowledgeTEESigner",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "provider", "type": "address"}
        ],
        "name": "acknowledgeTEESignerByOwner",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "user", "type": "address"},
            {"internalType": "address", "name": "provider", "type": "address"},
            {"internalType": "string", "name": "additionalInfo", "type": "string"},
        ],
        "name": "addAccount",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "user", "type": "address"},
            {"internalType": "string", "name": "id", "type": "string"},
            {"internalType": "bytes", "name": "modelRootHash", "type": "bytes"},
        ],
        "name": "addDeliverable",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "string", "name": "url", "type": "string"},
            {
                "components": [
                    {"internalType": "uint256", "name": "cpuCount", "type": "uint256"},
                    {"internalType": "uint256", "name": "nodeMemory", "type": "uint256"},
                    {"internalType": "uint256", "name": "gpuCount", "type": "uint256"},
                    {"internalType": "uint256", "name": "nodeStorage", "type": "uint256"},
                    {"internalType": "string", "name": "gpuType", "type": "string"},
                ],
                "internalType": "struct Quota",
                "name": "quota",
                "type": "tuple",
            },
            {"internalType": "uint256", "name": "pricePerToken", "type": "uint256"},
            {"internalType": "bool", "name": "occupied", "type": "bool"},
            {"internalType": "string[]", "name": "models", "type": "string[]"},
            {"internalType": "address", "name": "teeSignerAddress", "type": "address"},
        ],
        "name": "addOrUpdateService",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "user", "type": "address"},
            {"internalType": "address", "name": "provider", "type": "address"},
        ],
        "name": "deleteAccount",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "user", "type": "address"},
            {"internalType": "address", "name": "provider", "type": "address"},
            {"internalType": "uint256", "name": "cancelRetrievingAmount", "type": "uint256"},
        ],
        "name": "depositFund",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "user", "type": "address"},
            {"internalType": "address", "name": "provider", "type": "address"},
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
                    {
                        "components": [
                            {"internalType": "uint256", "name": "index", "type": "uint256"},
                            {"internalType": "uint256", "name": "amount", "type": "uint256"},
                            {"internalType": "uint256", "name": "createdAt", "type": "uint256"},
                            {"internalType": "bool", "name": "_deprecated_processed", "type": "bool"},
                        ],
                        "internalType": "struct Refund[]",
                        "name": "refunds",
                        "type": "tuple[]",
                    },
                    {"internalType": "string", "name": "additionalInfo", "type": "string"},
                    {
                        "components": [
                            {"internalType": "string", "name": "id", "type": "string"},
                            {"internalType": "bytes", "name": "modelRootHash", "type": "bytes"},
                            {"internalType": "bytes", "name": "encryptedSecret", "type": "bytes"},
                            {"internalType": "bool", "name": "acknowledged", "type": "bool"},
                            {"internalType": "uint248", "name": "timestamp", "type": "uint248"},
                            {"internalType": "bool", "name": "settled", "type": "bool"},
                        ],
                        "internalType": "struct Deliverable[]",
                        "name": "deliverables",
                        "type": "tuple[]",
                    },
                    {"internalType": "uint256", "name": "validRefundsLength", "type": "uint256"},
                    {"internalType": "uint256", "name": "deliverablesHead", "type": "uint256"},
                    {"internalType": "uint256", "name": "deliverablesCount", "type": "uint256"},
                    {"internalType": "bool", "name": "acknowledged", "type": "bool"},
                ],
                "internalType": "struct AccountDetails",
                "name": "",
                "type": "tuple",
            }
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "provider", "type": "address"},
            {"internalType": "uint256", "name": "offset", "type": "uint256"},
            {"internalType": "uint256", "name": "limit", "type": "uint256"},
        ],
        "name": "getAccountsByProvider",
        "outputs": [
            {
                "components": [
                    {"internalType": "address", "name": "user", "type": "address"},
                    {"internalType": "address", "name": "provider", "type": "address"},
                    {"internalType": "uint256", "name": "nonce", "type": "uint256"},
                    {"internalType": "uint256", "name": "balance", "type": "uint256"},
                    {"internalType": "uint256", "name": "pendingRefund", "type": "uint256"},
                    {"internalType": "string", "name": "additionalInfo", "type": "string"},
                    {"internalType": "uint256", "name": "validRefundsLength", "type": "uint256"},
                    {"internalType": "uint256", "name": "deliverablesCount", "type": "uint256"},
                    {"internalType": "bool", "name": "acknowledged", "type": "bool"},
                ],
                "internalType": "struct AccountSummary[]",
                "name": "accounts",
                "type": "tuple[]",
            },
            {"internalType": "uint256", "name": "total", "type": "uint256"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "user", "type": "address"},
            {"internalType": "uint256", "name": "offset", "type": "uint256"},
            {"internalType": "uint256", "name": "limit", "type": "uint256"},
        ],
        "name": "getAccountsByUser",
        "outputs": [
            {
                "components": [
                    {"internalType": "address", "name": "user", "type": "address"},
                    {"internalType": "address", "name": "provider", "type": "address"},
                    {"internalType": "uint256", "name": "nonce", "type": "uint256"},
                    {"internalType": "uint256", "name": "balance", "type": "uint256"},
                    {"internalType": "uint256", "name": "pendingRefund", "type": "uint256"},
                    {"internalType": "string", "name": "additionalInfo", "type": "string"},
                    {"internalType": "uint256", "name": "validRefundsLength", "type": "uint256"},
                    {"internalType": "uint256", "name": "deliverablesCount", "type": "uint256"},
                    {"internalType": "bool", "name": "acknowledged", "type": "bool"},
                ],
                "internalType": "struct AccountSummary[]",
                "name": "accounts",
                "type": "tuple[]",
            },
            {"internalType": "uint256", "name": "total", "type": "uint256"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "offset", "type": "uint256"},
            {"internalType": "uint256", "name": "limit", "type": "uint256"},
        ],
        "name": "getAllAccounts",
        "outputs": [
            {
                "components": [
                    {"internalType": "address", "name": "user", "type": "address"},
                    {"internalType": "address", "name": "provider", "type": "address"},
                    {"internalType": "uint256", "name": "nonce", "type": "uint256"},
                    {"internalType": "uint256", "name": "balance", "type": "uint256"},
                    {"internalType": "uint256", "name": "pendingRefund", "type": "uint256"},
                    {"internalType": "string", "name": "additionalInfo", "type": "string"},
                    {"internalType": "uint256", "name": "validRefundsLength", "type": "uint256"},
                    {"internalType": "uint256", "name": "deliverablesCount", "type": "uint256"},
                    {"internalType": "bool", "name": "acknowledged", "type": "bool"},
                ],
                "internalType": "struct AccountSummary[]",
                "name": "accounts",
                "type": "tuple[]",
            },
            {"internalType": "uint256", "name": "total", "type": "uint256"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "getAllServices",
        "outputs": [
            {
                "components": [
                    {"internalType": "address", "name": "provider", "type": "address"},
                    {"internalType": "string", "name": "url", "type": "string"},
                    {
                        "components": [
                            {"internalType": "uint256", "name": "cpuCount", "type": "uint256"},
                            {"internalType": "uint256", "name": "nodeMemory", "type": "uint256"},
                            {"internalType": "uint256", "name": "gpuCount", "type": "uint256"},
                            {"internalType": "uint256", "name": "nodeStorage", "type": "uint256"},
                            {"internalType": "string", "name": "gpuType", "type": "string"},
                        ],
                        "internalType": "struct Quota",
                        "name": "quota",
                        "type": "tuple",
                    },
                    {"internalType": "uint256", "name": "pricePerToken", "type": "uint256"},
                    {"internalType": "bool", "name": "occupied", "type": "bool"},
                    {"internalType": "string[]", "name": "models", "type": "string[]"},
                    {"internalType": "address", "name": "teeSignerAddress", "type": "address"},
                    {"internalType": "bool", "name": "teeSignerAcknowledged", "type": "bool"},
                ],
                "internalType": "struct Service[]",
                "name": "services",
                "type": "tuple[]",
            }
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "address[]", "name": "users", "type": "address[]"}
        ],
        "name": "getBatchAccountsByUsers",
        "outputs": [
            {
                "components": [
                    {"internalType": "address", "name": "user", "type": "address"},
                    {"internalType": "address", "name": "provider", "type": "address"},
                    {"internalType": "uint256", "name": "nonce", "type": "uint256"},
                    {"internalType": "uint256", "name": "balance", "type": "uint256"},
                    {"internalType": "uint256", "name": "pendingRefund", "type": "uint256"},
                    {"internalType": "string", "name": "additionalInfo", "type": "string"},
                    {"internalType": "uint256", "name": "validRefundsLength", "type": "uint256"},
                    {"internalType": "uint256", "name": "deliverablesCount", "type": "uint256"},
                    {"internalType": "bool", "name": "acknowledged", "type": "bool"},
                ],
                "internalType": "struct AccountSummary[]",
                "name": "accounts",
                "type": "tuple[]",
            }
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "user", "type": "address"},
            {"internalType": "address", "name": "provider", "type": "address"},
            {"internalType": "string", "name": "id", "type": "string"},
        ],
        "name": "getDeliverable",
        "outputs": [
            {
                "components": [
                    {"internalType": "string", "name": "id", "type": "string"},
                    {"internalType": "bytes", "name": "modelRootHash", "type": "bytes"},
                    {"internalType": "bytes", "name": "encryptedSecret", "type": "bytes"},
                    {"internalType": "bool", "name": "acknowledged", "type": "bool"},
                    {"internalType": "uint248", "name": "timestamp", "type": "uint248"},
                    {"internalType": "bool", "name": "settled", "type": "bool"},
                ],
                "internalType": "struct Deliverable",
                "name": "",
                "type": "tuple",
            }
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "user", "type": "address"},
            {"internalType": "address", "name": "provider", "type": "address"},
        ],
        "name": "getDeliverables",
        "outputs": [
            {
                "components": [
                    {"internalType": "string", "name": "id", "type": "string"},
                    {"internalType": "bytes", "name": "modelRootHash", "type": "bytes"},
                    {"internalType": "bytes", "name": "encryptedSecret", "type": "bytes"},
                    {"internalType": "bool", "name": "acknowledged", "type": "bool"},
                    {"internalType": "uint248", "name": "timestamp", "type": "uint248"},
                    {"internalType": "bool", "name": "settled", "type": "bool"},
                ],
                "internalType": "struct Deliverable[]",
                "name": "",
                "type": "tuple[]",
            }
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "user", "type": "address"},
            {"internalType": "address", "name": "provider", "type": "address"},
        ],
        "name": "getPendingRefund",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "provider", "type": "address"}
        ],
        "name": "getService",
        "outputs": [
            {
                "components": [
                    {"internalType": "address", "name": "provider", "type": "address"},
                    {"internalType": "string", "name": "url", "type": "string"},
                    {
                        "components": [
                            {"internalType": "uint256", "name": "cpuCount", "type": "uint256"},
                            {"internalType": "uint256", "name": "nodeMemory", "type": "uint256"},
                            {"internalType": "uint256", "name": "gpuCount", "type": "uint256"},
                            {"internalType": "uint256", "name": "nodeStorage", "type": "uint256"},
                            {"internalType": "string", "name": "gpuType", "type": "string"},
                        ],
                        "internalType": "struct Quota",
                        "name": "quota",
                        "type": "tuple",
                    },
                    {"internalType": "uint256", "name": "pricePerToken", "type": "uint256"},
                    {"internalType": "bool", "name": "occupied", "type": "bool"},
                    {"internalType": "string[]", "name": "models", "type": "string[]"},
                    {"internalType": "address", "name": "teeSignerAddress", "type": "address"},
                    {"internalType": "bool", "name": "teeSignerAcknowledged", "type": "bool"},
                ],
                "internalType": "struct Service",
                "name": "service",
                "type": "tuple",
            }
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "_locktime", "type": "uint256"},
            {"internalType": "address", "name": "_ledgerAddress", "type": "address"},
            {"internalType": "address", "name": "owner", "type": "address"},
            {"internalType": "uint256", "name": "_penaltyPercentage", "type": "uint256"},
        ],
        "name": "initialize",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "initialized",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "ledgerAddress",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "lockTime",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "owner",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "penaltyPercentage",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "user", "type": "address"},
            {"internalType": "address", "name": "provider", "type": "address"},
        ],
        "name": "processRefund",
        "outputs": [
            {"internalType": "uint256", "name": "totalAmount", "type": "uint256"},
            {"internalType": "uint256", "name": "balance", "type": "uint256"},
            {"internalType": "uint256", "name": "pendingRefund", "type": "uint256"},
        ],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "removeService",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "renounceOwnership",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "user", "type": "address"},
            {"internalType": "address", "name": "provider", "type": "address"},
        ],
        "name": "requestRefundAll",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "provider", "type": "address"}
        ],
        "name": "revokeTEESignerAcknowledgement",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {
                "components": [
                    {"internalType": "string", "name": "id", "type": "string"},
                    {"internalType": "bytes", "name": "encryptedSecret", "type": "bytes"},
                    {"internalType": "bytes", "name": "modelRootHash", "type": "bytes"},
                    {"internalType": "uint256", "name": "nonce", "type": "uint256"},
                    {"internalType": "bytes", "name": "signature", "type": "bytes"},
                    {"internalType": "uint256", "name": "taskFee", "type": "uint256"},
                    {"internalType": "address", "name": "user", "type": "address"},
                ],
                "internalType": "struct VerifierInput",
                "name": "verifierInput",
                "type": "tuple",
            }
        ],
        "name": "settleFees",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "bytes4", "name": "interfaceId", "type": "bytes4"}
        ],
        "name": "supportsInterface",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "newOwner", "type": "address"}
        ],
        "name": "transferOwnership",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "_locktime", "type": "uint256"}
        ],
        "name": "updateLockTime",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "_penaltyPercentage", "type": "uint256"}
        ],
        "name": "updatePenaltyPercentage",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {"stateMutability": "payable", "type": "receive"},
]
