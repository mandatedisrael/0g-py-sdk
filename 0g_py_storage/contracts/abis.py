"""
Smart contract ABIs and addresses for 0G Storage.

Ported from official TypeScript SDK:
node_modules/@0glabs/0g-ts-sdk/lib.commonjs/contracts/flow/factories/FixedPriceFlow__factory.js

NOTE: Contract addresses sourced from https://docs.0g.ai/developer-hub/testnet/testnet-overview
"""

# Flow contract ABI - Key functions extracted from TS SDK
# Full ABI available in FixedPriceFlow__factory.js
FLOW_CONTRACT_ABI = [
    # submit function - Main function for uploading files
    {
        "inputs": [
            {
                "components": [
                    {
                        "internalType": "uint256",
                        "name": "length",
                        "type": "uint256",
                    },
                    {
                        "internalType": "bytes",
                        "name": "tags",
                        "type": "bytes",
                    },
                    {
                        "components": [
                            {
                                "internalType": "bytes32",
                                "name": "root",
                                "type": "bytes32",
                            },
                            {
                                "internalType": "uint256",
                                "name": "height",
                                "type": "uint256",
                            },
                        ],
                        "internalType": "struct SubmissionNode[]",
                        "name": "nodes",
                        "type": "tuple[]",
                    },
                ],
                "internalType": "struct Submission",
                "name": "submission",
                "type": "tuple",
            },
        ],
        "name": "submit",
        "outputs": [
            {
                "internalType": "uint256",
                "name": "",
                "type": "uint256",
            },
            {
                "internalType": "bytes32",
                "name": "",
                "type": "bytes32",
            },
            {
                "internalType": "uint256",
                "name": "",
                "type": "uint256",
            },
            {
                "internalType": "uint256",
                "name": "",
                "type": "uint256",
            },
        ],
        "stateMutability": "payable",
        "type": "function",
    },
    # batchSubmit function - For batch uploads
    {
        "inputs": [
            {
                "components": [
                    {
                        "internalType": "uint256",
                        "name": "length",
                        "type": "uint256",
                    },
                    {
                        "internalType": "bytes",
                        "name": "tags",
                        "type": "bytes",
                    },
                    {
                        "components": [
                            {
                                "internalType": "bytes32",
                                "name": "root",
                                "type": "bytes32",
                            },
                            {
                                "internalType": "uint256",
                                "name": "height",
                                "type": "uint256",
                            },
                        ],
                        "internalType": "struct SubmissionNode[]",
                        "name": "nodes",
                        "type": "tuple[]",
                    },
                ],
                "internalType": "struct Submission[]",
                "name": "submissions",
                "type": "tuple[]",
            },
        ],
        "name": "batchSubmit",
        "outputs": [
            {
                "internalType": "uint256[]",
                "name": "indexes",
                "type": "uint256[]",
            },
            {
                "internalType": "bytes32[]",
                "name": "digests",
                "type": "bytes32[]",
            },
            {
                "internalType": "uint256[]",
                "name": "startIndexes",
                "type": "uint256[]",
            },
            {
                "internalType": "uint256[]",
                "name": "lengths",
                "type": "uint256[]",
            },
        ],
        "stateMutability": "payable",
        "type": "function",
    },
    # Submit event - Emitted on successful submission
    {
        "anonymous": False,
        "inputs": [
            {
                "indexed": True,
                "internalType": "address",
                "name": "sender",
                "type": "address",
            },
            {
                "indexed": True,
                "internalType": "bytes32",
                "name": "identity",
                "type": "bytes32",
            },
            {
                "indexed": False,
                "internalType": "uint256",
                "name": "submissionIndex",
                "type": "uint256",
            },
            {
                "indexed": False,
                "internalType": "uint256",
                "name": "startPos",
                "type": "uint256",
            },
            {
                "indexed": False,
                "internalType": "uint256",
                "name": "length",
                "type": "uint256",
            },
            {
                "components": [
                    {
                        "internalType": "uint256",
                        "name": "length",
                        "type": "uint256",
                    },
                    {
                        "internalType": "bytes",
                        "name": "tags",
                        "type": "bytes",
                    },
                    {
                        "components": [
                            {
                                "internalType": "bytes32",
                                "name": "root",
                                "type": "bytes32",
                            },
                            {
                                "internalType": "uint256",
                                "name": "height",
                                "type": "uint256",
                            },
                        ],
                        "internalType": "struct SubmissionNode[]",
                        "name": "nodes",
                        "type": "tuple[]",
                    },
                ],
                "indexed": False,
                "internalType": "struct Submission",
                "name": "submission",
                "type": "tuple",
            },
        ],
        "name": "Submit",
        "type": "event",
    },
]

# Contract addresses from official 0G documentation
# Source: https://docs.0g.ai/developer-hub/testnet/testnet-overview

# Galileo Testnet
TESTNET_FLOW_ADDRESS = "0x22E03a6A89B950F1c82ec5e74F8eCa321a105296"
TESTNET_MINE_ADDRESS = "0x00A9E9604b0538e06b268Fb297Df333337f9593b"
TESTNET_REWARD_ADDRESS = "0xA97B57b4BdFEA2D0a25e535bd849ad4e6C440A69"

# Mainnet (placeholder - update when mainnet launches)
MAINNET_FLOW_ADDRESS = None  # To be announced
MAINNET_MINE_ADDRESS = None  # To be announced
MAINNET_REWARD_ADDRESS = None  # To be announced

# Network configurations
NETWORK_ADDRESSES = {
    "testnet": {
        "flow": TESTNET_FLOW_ADDRESS,
        "mine": TESTNET_MINE_ADDRESS,
        "reward": TESTNET_REWARD_ADDRESS,
        "chain_id": 16600,
    },
    "mainnet": {
        "flow": MAINNET_FLOW_ADDRESS,
        "mine": MAINNET_MINE_ADDRESS,
        "reward": MAINNET_REWARD_ADDRESS,
        "chain_id": 16601,
    }
}


def get_flow_contract_address(network: str = "testnet") -> str:
    """
    Get Flow contract address for specified network.

    Args:
        network: Network name ("testnet" or "mainnet")

    Returns:
        Flow contract address

    Raises:
        ValueError: If network is invalid or mainnet not available
    """
    if network not in NETWORK_ADDRESSES:
        raise ValueError(f"Invalid network: {network}. Must be 'testnet' or 'mainnet'")

    address = NETWORK_ADDRESSES[network]["flow"]
    if address is None:
        raise ValueError(f"Flow contract address not available for {network}")

    return address
