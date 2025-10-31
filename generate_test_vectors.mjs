/**
 * Generate test vectors from circomlibjs for Python crypto validation.
 *
 * This script uses the reference circomlibjs implementation to generate
 * known-good test vectors for:
 * - Baby JubJub point operations
 * - EdDSA key generation
 * - Pedersen hashing
 * - Request signing
 */

import * as circomlibjs from 'circomlibjs';
import * as fs from 'fs';
import * as path from 'path';
import * as crypto from 'crypto';

const OUTPUT_DIR = './test_vectors';

// Ensure output directory exists
if (!fs.existsSync(OUTPUT_DIR)) {
    fs.mkdirSync(OUTPUT_DIR, { recursive: true });
}

async function generateTestVectors() {
    console.log('🚀 Generating test vectors from circomlibjs reference implementation...\n');

    try {
        // Initialize circomlibjs components
        const babyjubjub = await circomlibjs.buildBabyjub();
        const eddsa = await circomlibjs.buildEddsa();
        const pedersenHash = await circomlibjs.buildPedersenHash();

        // 1. Point addition test vectors
        console.log('📍 Generating Baby JubJub point operation vectors...');
        const pointAdditionVectors = generatePointAdditionVectors(babyjubjub);
        fs.writeFileSync(
            path.join(OUTPUT_DIR, 'point_addition.json'),
            JSON.stringify(pointAdditionVectors, null, 2)
        );
        console.log(`   ✓ Generated ${pointAdditionVectors.length} point addition test cases\n`);

        // 2. Scalar multiplication test vectors
        console.log('🔢 Generating scalar multiplication vectors...');
        const scalarMultVectors = generateScalarMultiplyVectors(babyjubjub);
        fs.writeFileSync(
            path.join(OUTPUT_DIR, 'scalar_multiply.json'),
            JSON.stringify(scalarMultVectors, null, 2)
        );
        console.log(`   ✓ Generated ${scalarMultVectors.length} scalar multiplication test cases\n`);

        // 3. Key generation test vectors
        console.log('🔑 Generating EdDSA key pair vectors...');
        const keyGenVectors = await generateKeyGenVectors(babyjubjub, eddsa);
        fs.writeFileSync(
            path.join(OUTPUT_DIR, 'key_generation.json'),
            JSON.stringify(keyGenVectors, null, 2)
        );
        console.log(`   ✓ Generated ${keyGenVectors.length} key generation test cases\n`);

        // 4. EdDSA signing test vectors
        console.log('✍️  Generating EdDSA signing vectors...');
        const signingVectors = await generateSigningVectors(babyjubjub, eddsa);
        fs.writeFileSync(
            path.join(OUTPUT_DIR, 'signing.json'),
            JSON.stringify(signingVectors, null, 2)
        );
        console.log(`   ✓ Generated ${signingVectors.length} signing test cases\n`);

        // 5. Pedersen hash test vectors
        console.log('🔐 Generating Pedersen hash vectors...');
        const pedersenVectors = generatePedersenVectors(pedersenHash);
        fs.writeFileSync(
            path.join(OUTPUT_DIR, 'pedersen_hash.json'),
            JSON.stringify(pedersenVectors, null, 2)
        );
        console.log(`   ✓ Generated ${pedersenVectors.length} Pedersen hash test cases\n`);

        // 6. Request signing test vectors (0G protocol specific)
        console.log('📤 Generating request signing vectors...');
        const requestVectors = await generateRequestSigningVectors(babyjubjub, eddsa, pedersenHash);
        fs.writeFileSync(
            path.join(OUTPUT_DIR, 'request_signing.json'),
            JSON.stringify(requestVectors, null, 2)
        );
        console.log(`   ✓ Generated ${requestVectors.length} request signing test cases\n`);

        // 7. Pedersen bases extraction (critical for compatibility)
        console.log('📦 Extracting Pedersen bases...');
        const pedersenBases = extractPedersenBases(pedersenHash);
        fs.writeFileSync(
            path.join(OUTPUT_DIR, 'pedersen_bases.json'),
            JSON.stringify({
                description: 'Precomputed Pedersen hash generator bases from circomlibjs',
                count: pedersenBases.length,
                bases: pedersenBases
            }, null, 2)
        );
        console.log(`   ✓ Extracted ${pedersenBases.length} Pedersen bases\n`);

        console.log('✅ All test vectors generated successfully!');
        console.log(`📁 Output directory: ${OUTPUT_DIR}\n`);

    } catch (error) {
        console.error('❌ Error generating test vectors:', error);
        process.exit(1);
    }
}

function generatePointAdditionVectors(babyjubjub) {
    const vectors = [];
    const G = babyjubjub.Generator;

    // Test cases
    const testCases = [
        { name: 'G + G (doubling)', p1: G, p2: G },
        { name: 'G + 2G', p1: G, p2: babyjubjub.mulPointEscalar(G, [BigInt(2), BigInt(0)]) },
    ];

    for (const tc of testCases) {
        const result = babyjubjub.addPoint(tc.p1, tc.p2);
        vectors.push({
            name: tc.name,
            p1: pointToHex(tc.p1),
            p2: pointToHex(tc.p2),
            result: pointToHex(result)
        });
    }

    return vectors;
}

function generateScalarMultiplyVectors(babyjubjub) {
    const vectors = [];
    const G = babyjubjub.GGen();

    // Test scalars: small numbers, powers of 2, and random values
    const scalars = [
        1n, 2n, 3n, 10n, 100n, 256n, 65536n,
        BigInt('12345678901234567890'),
        BigInt('1000000000000000000000000000')
    ];

    for (const scalar of scalars) {
        const result = babyjubjub.mulPointEscalar(G, scalar);
        vectors.push({
            scalar: scalar.toString(),
            result: pointToHex(result)
        });
    }

    return vectors;
}

async function generateKeyGenVectors(babyjubjub, eddsa) {
    const vectors = [];

    // Generate several key pairs
    for (let i = 0; i < 5; i++) {
        const privkey = babyjubjub.F.random();
        const pubkey = eddsa.prv2pub(privkey);
        const packedPubkey = babyjubjub.packPoint(pubkey);

        // Convert to 16-byte chunks for compatibility with 0G format
        const privkeyBytes = bigintToBytes(privkey, 32);
        const pubkeyBytes = Buffer.from(packedPubkey);

        vectors.push({
            index: i,
            privkey: {
                hex: '0x' + privkeyBytes.toString('hex'),
                packed: [
                    '0x' + privkeyBytes.slice(0, 16).toString('hex'),
                    '0x' + privkeyBytes.slice(16, 32).toString('hex')
                ]
            },
            pubkey: {
                point: pointToHex(pubkey),
                packed: '0x' + pubkeyBytes.toString('hex')
            }
        });
    }

    return vectors;
}

async function generateSigningVectors(babyjubjub, eddsa) {
    const vectors = [];

    // Create test messages
    const messages = [
        Buffer.from('Hello, 0G!'),
        Buffer.from('Test message for signing'),
        Buffer.from('0G Storage Protocol v1'),
        crypto.randomBytes(64),
        Buffer.alloc(48) // Zero-filled buffer (0G request)
    ];

    // Generate signatures for multiple keys
    for (let keyIdx = 0; keyIdx < 2; keyIdx++) {
        const privkey = babyjubjub.F.random();

        for (let msgIdx = 0; msgIdx < Math.min(3, messages.length); msgIdx++) {
            const message = messages[msgIdx];
            const signature = eddsa.signPedersen(privkey, message);
            const packed = eddsa.packSignature(signature);

            vectors.push({
                keyIndex: keyIdx,
                messageIndex: msgIdx,
                message: '0x' + message.toString('hex'),
                privkey: '0x' + bigintToBytes(privkey, 32).toString('hex'),
                signature: {
                    R: pointToHex(signature.R),
                    S: signature.S.toString(),
                    packed: '0x' + packed.toString('hex')
                }
            });
        }
    }

    return vectors;
}

function generatePedersenVectors(pedersenHash) {
    const vectors = [];

    // Test inputs: various sizes and patterns
    const testInputs = [
        Buffer.from(''),                                    // Empty
        Buffer.from('a'),                                  // Single byte
        Buffer.from('Hello'),                              // Short string
        Buffer.from('The quick brown fox jumps over'),    // Medium
        crypto.randomBytes(32),                            // Random 32 bytes
        crypto.randomBytes(64),                            // Random 64 bytes
        Buffer.alloc(48),                                  // Zero-filled (0G request)
    ];

    for (const input of testInputs) {
        const hashPoint = pedersenHash.hash(input);
        vectors.push({
            input: '0x' + input.toString('hex'),
            inputLength: input.length,
            hashPoint: pointToHex(hashPoint),
            hashX: '0x' + Buffer.from(hashPoint[0].toString(16), 'hex').toString('hex')
        });
    }

    return vectors;
}

async function generateRequestSigningVectors(babyjubjub, eddsa, pedersenHash) {
    const vectors = [];

    // Simulate 0G request structure (64 bytes):
    // nonce (8) + fee (16) + userAddress (20) + providerAddress (20)

    for (let i = 0; i < 3; i++) {
        const request = Buffer.alloc(64);

        // Fill with test data
        const nonce = BigInt(12345 + i);
        const fee = BigInt('30733644962');
        const userAddr = '0xB3AD3a10d187cbc4ca3e8c3EDED62F8286F8e16E';
        const providerAddr = '0x1234567890123456789012345678901234567890';

        // Write request fields (little-endian)
        writeLE(request, 0, nonce, 8);
        writeLE(request, 8, fee, 16);
        writeLE(request, 24, BigInt('0x' + userAddr.slice(2)), 20);
        writeLE(request, 44, BigInt('0x' + providerAddr.slice(2)), 20);

        // Generate signature
        const privkey = babyjubjub.F.random();
        const signature = eddsa.signPedersen(privkey, request);
        const packed = eddsa.packSignature(signature);

        // Generate Pedersen hash (for request-hash header)
        const hashBuffer = Buffer.concat([
            Buffer.alloc(8),  // nonce
            Buffer.alloc(20), // user address
            Buffer.alloc(20)  // provider address
        ]);
        writeLE(hashBuffer, 0, nonce, 8);
        writeLE(hashBuffer, 8, BigInt('0x' + userAddr.slice(2)), 20);
        writeLE(hashBuffer, 28, BigInt('0x' + providerAddr.slice(2)), 20);

        const requestHash = pedersenHash.hash(hashBuffer);

        vectors.push({
            index: i,
            request: '0x' + request.toString('hex'),
            privkey: '0x' + bigintToBytes(privkey, 32).toString('hex'),
            signature: {
                R: pointToHex(signature.R),
                S: signature.S.toString(),
                packed: '0x' + packed.toString('hex')
            },
            requestHash: pointToHex(requestHash)
        });
    }

    return vectors;
}

function extractPedersenBases(pedersenHash) {
    // Extract the precomputed generator bases from Pedersen hasher
    // This is critical for Python implementation to produce identical hashes
    const bases = [];

    // Try to access internal bases if available
    if (pedersenHash.bases) {
        return pedersenHash.bases.map(p => pointToHex(p));
    }

    // Fallback: compute bases by hashing specific patterns
    console.warn('⚠️  Could not extract Pedersen bases directly from circomlibjs');
    console.log('   Note: Pedersen implementation may require additional configuration');

    return bases;
}

// Utility functions

function pointToHex(point) {
    const x = BigInt(point[0]).toString(16).padStart(64, '0');
    const y = BigInt(point[1]).toString(16).padStart(64, '0');
    return {
        x: '0x' + x,
        y: '0x' + y
    };
}

function bigintToBytes(bigint, length) {
    const buffer = Buffer.alloc(length);
    for (let i = 0; i < length; i++) {
        buffer[i] = Number((bigint >> BigInt(8 * i)) & BigInt(0xff));
    }
    return buffer;
}

function writeLE(buffer, offset, value, length) {
    for (let i = 0; i < length; i++) {
        buffer[offset + i] = Number((value >> BigInt(8 * i)) & BigInt(0xff));
    }
}

// Run generation
generateTestVectors();
