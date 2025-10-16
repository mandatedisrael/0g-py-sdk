"""
Authentication and signature management for the 0G Compute Network SDK.

This module handles:
- Request header generation with Baby JubJub signatures
- Pedersen hash calculation using circomlibjs via Node.js bridge
- Fee calculation and billing proofs
- Response verification for TEE services

Uses circomlibjs cryptographic primitives via Node.js subprocess for compatibility.
"""

from typing import Dict, Any, Optional, List, Tuple
from web3 import Web3
from web3.contract import Contract
from eth_account.signers.local import LocalAccount
import json
import subprocess
import tempfile
import os
from pathlib import Path

from .exceptions import AuthenticationError, InvalidResponseError, ConfigurationError


class Request:
    """
    Request structure for billing.
    
    Serializes to 64 bytes:
    - nonce: 8 bytes
    - fee: 16 bytes  
    - user_address: 20 bytes
    - provider_address: 20 bytes
    """
    
    NONCE_LENGTH = 8
    FEE_LENGTH = 16
    ADDR_LENGTH = 20
    
    def __init__(self, nonce: int, fee: int, user_address: str, provider_address: str):
        self.nonce = nonce
        self.fee = fee
        # Convert addresses to int, removing 0x prefix if present
        self.user_address = int(user_address.replace('0x', ''), 16)
        self.provider_address = int(provider_address.replace('0x', ''), 16)
    
    def serialize(self) -> bytes:
        """
        Serialize request to 64-byte binary format.
        Layout: nonce(8) + fee(16) + userAddress(20) + providerAddress(20)
        
        Uses little-endian byte order to match TypeScript implementation.
        """
        buffer = bytearray(64)
        offset = 0
        
        # Write nonce (8 bytes, little-endian)
        nonce_bytes = self._bigint_to_bytes_le(self.nonce, self.NONCE_LENGTH)
        buffer[offset:offset+8] = nonce_bytes
        offset += 8
        
        # Write fee (16 bytes, little-endian)
        fee_bytes = self._bigint_to_bytes_le(self.fee, self.FEE_LENGTH)
        buffer[offset:offset+16] = fee_bytes
        offset += 16
        
        # Write user address (20 bytes, little-endian)
        user_bytes = self._bigint_to_bytes_le(self.user_address, self.ADDR_LENGTH)
        buffer[offset:offset+20] = user_bytes
        offset += 20
        
        # Write provider address (20 bytes, little-endian)
        provider_bytes = self._bigint_to_bytes_le(self.provider_address, self.ADDR_LENGTH)
        buffer[offset:offset+20] = provider_bytes
        
        return bytes(buffer)
    
    @staticmethod
    def _bigint_to_bytes_le(value: int, length: int) -> bytes:
        """Convert integer to little-endian bytes (matches TypeScript implementation)."""
        result = bytearray(length)
        for i in range(length):
            result[i] = (value >> (8 * i)) & 0xff
        return bytes(result)
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary for JSON serialization."""
        return {
            'nonce': str(self.nonce),
            'fee': str(self.fee),
            'userAddress': f"0x{self.user_address:040x}",
            'providerAddress': f"0x{self.provider_address:040x}"
        }


class CircomlibBridge:
    """
    Bridge to circomlibjs via Node.js subprocess.
    
    This ensures 100% compatibility with the TypeScript SDK by using
    the actual circomlibjs library for cryptographic operations.
    """
    
    def __init__(self):
        self._node_script = self._create_node_script()
    
    def _create_node_script(self) -> str:
        """Create Node.js script that wraps circomlibjs functions."""
        return """
const circomlibjs = require('circomlibjs');

async function main() {
    const operation = process.argv[2];
    const data = process.argv[3] ? JSON.parse(process.argv[3]) : null;
    
    try {
        let result;
        
        if (operation === 'genKeyPair') {
            result = await genKeyPair();
        } else if (operation === 'signData') {
            result = await signData(data.requests, data.privateKey);
        } else if (operation === 'pedersenHash') {
            result = await pedersenHash(data.buffer);
        } else {
            throw new Error('Unknown operation: ' + operation);
        }
        
        console.log(JSON.stringify(result));
    } catch (error) {
        console.error(JSON.stringify({ error: error.message }));
        process.exit(1);
    }
}

async function genKeyPair() {
    const babyjubjub = await circomlibjs.buildBabyjub();
    const eddsa = await circomlibjs.buildEddsa();
    
    const privkey = babyjubjub.F.random();
    const pubkey = eddsa.prv2pub(privkey);
    const packedPubkey = babyjubjub.packPoint(pubkey);
    
    const BIGINT_SIZE = 16;
    const packedPubkey0 = bytesToBigint(packedPubkey.slice(0, BIGINT_SIZE));
    const packedPubkey1 = bytesToBigint(packedPubkey.slice(BIGINT_SIZE));
    const packPrivkey0 = bytesToBigint(privkey.slice(0, BIGINT_SIZE));
    const packPrivkey1 = bytesToBigint(privkey.slice(BIGINT_SIZE));
    
    return {
        packedPrivkey: [packPrivkey0.toString(), packPrivkey1.toString()],
        doublePackedPubkey: [packedPubkey0.toString(), packedPubkey1.toString()]
    };
}

async function signData(requests, packedPrivkey) {
    const eddsa = await circomlibjs.buildEddsa();
    const BIGINT_SIZE = 16;
    const FIELD_SIZE = 32;
    
    const packedPrivkey0 = bigintToBytes(BigInt(packedPrivkey[0]), BIGINT_SIZE);
    const packedPrivkey1 = bigintToBytes(BigInt(packedPrivkey[1]), BIGINT_SIZE);
    
    const privateKey = new Uint8Array(FIELD_SIZE);
    privateKey.set(packedPrivkey0, 0);
    privateKey.set(packedPrivkey1, BIGINT_SIZE);
    
    const signatures = [];
    for (const request of requests) {
        const requestBytes = Buffer.from(request, 'hex');
        const signature = eddsa.signPedersen(privateKey, requestBytes);
        const packed = eddsa.packSignature(signature);
        signatures.push(Array.from(packed));
    }
    
    return signatures;
}

async function pedersenHash(bufferHex) {
    const h = await circomlibjs.buildPedersenHash();
    const buffer = Buffer.from(bufferHex, 'hex');
    const hash = h.hash(buffer);
    return '0x' + Buffer.from(hash).toString('hex');
}

function bigintToBytes(bigint, length) {
    const bytes = new Uint8Array(length);
    for (let i = 0; i < length; i++) {
        bytes[i] = Number((bigint >> BigInt(8 * i)) & BigInt(0xff));
    }
    return bytes;
}

function bytesToBigint(bytes) {
    let bigint = BigInt(0);
    for (let i = 0; i < bytes.length; i++) {
        bigint += BigInt(bytes[i]) << BigInt(8 * i);
    }
    return bigint;
}

main();
"""
    
    def call_node(self, operation: str, data: Any = None) -> Any:
        """Call Node.js script with circomlibjs operation."""
        try:
            # Write script to temp file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
                f.write(self._node_script)
                script_path = f.name
            
            # Prepare command
            cmd = ['node', script_path, operation]
            if data:
                cmd.append(json.dumps(data))
            
            # Execute (set NODE_PATH so Node can find node_modules)
            project_root = Path(__file__).parent.parent
            node_modules_path = project_root / 'node_modules'
            env = os.environ.copy()
            env['NODE_PATH'] = str(node_modules_path)

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                env=env
            )
            
            # Clean up
            os.unlink(script_path)
            
            # Parse result
            return json.loads(result.stdout)
            
        except subprocess.CalledProcessError as e:
            raise AuthenticationError(f"circomlibjs operation failed: {e.stderr}")
        except Exception as e:
            raise AuthenticationError(f"Failed to call circomlibjs: {str(e)}")


class AuthManager:
    """
    Manages authentication using Baby JubJub curve cryptography via circomlibjs.
    
    This implements the 0G authentication protocol with full compatibility
    to the TypeScript SDK.
    """
    
    def __init__(
        self,
        contract: Contract,
        account: LocalAccount,
        web3: Web3
    ):
        """Initialize the AuthManager."""
        self.contract = contract
        self.account = account
        self.web3 = web3
        self._nonce_counter = 0
        self._settle_signer_keys = {}
        self._circomlib = CircomlibBridge()
    
    def generate_request_headers(
        self,
        provider_address: str,
        content: str,
        input_fee: int = 0,
        output_fee: int = 0
    ) -> Dict[str, str]:
        """
        Generate authenticated request headers matching TypeScript SDK format.
        
        Args:
            provider_address: Provider's wallet address
            content: Request content
            input_fee: Fee for input (in wei)
            output_fee: Fee for output (in wei)
            
        Returns:
            Dictionary of authentication headers
        """
        try:
            # 1. Get or generate settlement signer key
            private_key = self._get_settlement_signer_key(provider_address)
            
            # 2. Generate unique nonce
            nonce = self._generate_nonce()
            
            # 3. Calculate total fee
            total_fee = input_fee + output_fee
            
            # 4. Create and serialize request
            request = Request(
                nonce=nonce,
                fee=total_fee,
                user_address=self.account.address,
                provider_address=provider_address
            )
            request_bytes = request.serialize()
            
            # 5. Sign request using circomlibjs
            signatures = self._circomlib.call_node('signData', {
                'requests': [request_bytes.hex()],
                'privateKey': private_key
            })
            signature = signatures[0]
            
            # 6. Calculate Pedersen hash
            request_hash = self._calculate_pedersen_hash(
                nonce,
                self.account.address,
                provider_address
            )
            
            # 7. Return headers in exact TypeScript format
            return {
                'X-Phala-Signature-Type': 'StandaloneApi',
                'Address': self.account.address,
                'Fee': str(total_fee),
                'Input-Fee': str(input_fee),
                'Nonce': str(nonce),
                'Request-Hash': request_hash,
                'Signature': json.dumps(signature),
                'VLLM-Proxy': 'true'
            }
            
        except Exception as e:
            raise AuthenticationError(f"Failed to generate headers: {str(e)}")
    
    def verify_response(
        self,
        provider_address: str,
        content: str,
        chat_id: str
    ) -> bool:
        """Verify TEE service response (placeholder for now)."""
        try:
            account_data = self.contract.functions.getAccount(
                self.account.address,
                provider_address
            ).call()
            
            tee_signer_address = account_data[9]
            
            if not tee_signer_address or tee_signer_address == "0x" + "0" * 40:
                return False
            
            # TODO: Implement actual TEE signature verification
            return True
            
        except Exception as e:
            raise InvalidResponseError(f"Failed to verify response: {str(e)}")
    
    def _get_settlement_signer_key(self, provider_address: str) -> List[str]:
        """Get or generate settlement signer key (2x16 bytes format)."""
        if provider_address in self._settle_signer_keys:
            return self._settle_signer_keys[provider_address]
        
        # Generate new key pair using circomlibjs
        key_pair = self._circomlib.call_node('genKeyPair')
        private_key = key_pair['packedPrivkey']
        
        self._settle_signer_keys[provider_address] = private_key
        return private_key
    
    def _calculate_pedersen_hash(
        self,
        nonce: int,
        user_address: str,
        provider_address: str
    ) -> str:
        """Calculate Pedersen hash using circomlibjs."""
        # Create 48-byte buffer: nonce(8) + userAddress(20) + providerAddress(20)
        buffer = bytearray(48)
        
        # Nonce (8 bytes, little-endian)
        nonce_bytes = Request._bigint_to_bytes_le(nonce, 8)
        buffer[0:8] = nonce_bytes
        
        # User address (20 bytes, little-endian)
        user_int = int(user_address.replace('0x', ''), 16)
        user_bytes = Request._bigint_to_bytes_le(user_int, 20)
        buffer[8:28] = user_bytes
        
        # Provider address (20 bytes, little-endian)
        provider_int = int(provider_address.replace('0x', ''), 16)
        provider_bytes = Request._bigint_to_bytes_le(provider_int, 20)
        buffer[28:48] = provider_bytes
        
        # Calculate hash using circomlibjs
        return self._circomlib.call_node('pedersenHash', {
            'buffer': buffer.hex()
        })
    
    def _generate_nonce(self) -> int:
        """Generate unique nonce."""
        self._nonce_counter += 1
        return self._nonce_counter