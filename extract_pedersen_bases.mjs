/**
 * Extract Pedersen hash generator bases from circomlibjs.
 *
 * These precomputed points are critical for Pedersen hash computation.
 * They must be extracted from the reference implementation to ensure
 * Python implementation produces identical hashes.
 */

import * as circomlibjs from 'circomlibjs';
import * as fs from 'fs';
import * as path from 'path';

const OUTPUT_FILE = './pedersen_bases.json';

async function extractBases() {
    console.log('🔐 Extracting Pedersen bases from circomlibjs...\n');

    try {
        const pedersenHash = await circomlibjs.buildPedersenHash();

        // Try to extract bases directly
        const bases = [];

        // Method 1: Try to access internal bases property
        if (pedersenHash.bases) {
            console.log('✓ Found bases in pedersenHash.bases');
            for (let i = 0; i < pedersenHash.bases.length; i++) {
                const base = pedersenHash.bases[i];
                bases.push({
                    index: i,
                    x: '0x' + BigInt(base[0]).toString(16).padStart(64, '0'),
                    y: '0x' + BigInt(base[1]).toString(16).padStart(64, '0')
                });
            }
        }

        // Method 2: Try to access _bases or other internal properties
        if (bases.length === 0 && pedersenHash._bases) {
            console.log('✓ Found bases in pedersenHash._bases');
            for (let i = 0; i < pedersenHash._bases.length; i++) {
                const base = pedersenHash._bases[i];
                bases.push({
                    index: i,
                    x: '0x' + BigInt(base[0]).toString(16).padStart(64, '0'),
                    y: '0x' + BigInt(base[1]).toString(16).padStart(64, '0')
                });
            }
        }

        // Method 3: Check all enumerable properties
        if (bases.length === 0) {
            console.log('⚠️  Could not find bases directly, checking properties...');
            const props = Object.getOwnPropertyNames(pedersenHash);
            console.log('   Available properties:', props.slice(0, 10).join(', '));

            // Try to find array-like property
            for (const prop of props) {
                if (Array.isArray(pedersenHash[prop]) && pedersenHash[prop].length > 100) {
                    console.log(`   Found potential bases array: ${prop} (length: ${pedersenHash[prop].length})`);
                    for (let i = 0; i < Math.min(10, pedersenHash[prop].length); i++) {
                        const item = pedersenHash[prop][i];
                        if (Array.isArray(item) && item.length === 2) {
                            bases.push({
                                index: i,
                                x: '0x' + BigInt(item[0]).toString(16).padStart(64, '0'),
                                y: '0x' + BigInt(item[1]).toString(16).padStart(64, '0')
                            });
                        }
                    }
                    if (bases.length > 0) {
                        console.log(`   ✓ Successfully extracted ${bases.length} bases from ${prop}`);
                        break;
                    }
                }
            }
        }

        // Fallback: Generate bases by computing Pedersen hash at specific points
        if (bases.length === 0) {
            console.log('\n⚠️  Could not extract bases from circomlibjs internals');
            console.log('   This is expected if circomlibjs uses a different API.');
            console.log('   Python implementation will need alternative approach.\n');

            // As fallback, we can at least document the structure needed
            const sampleData = {
                info: 'Pedersen bases not directly extractable from this circomlibjs version',
                note: 'Python implementation needs either:',
                options: [
                    '1. Direct export from circomlibjs source code',
                    '2. Hardcoding of known bases from reference implementation',
                    '3. Alternative Pedersen hash using SHA256 + point multiplication'
                ]
            };

            fs.writeFileSync(OUTPUT_FILE, JSON.stringify(sampleData, null, 2));
            console.log(`⚠️  Saved info to ${OUTPUT_FILE}\n`);
            return;
        }

        // Save to file
        const output = {
            timestamp: new Date().toISOString(),
            description: 'Pedersen hash generator bases from circomlibjs',
            count: bases.length,
            bases: bases
        };

        fs.writeFileSync(OUTPUT_FILE, JSON.stringify(output, null, 2));
        console.log(`✅ Extracted ${bases.length} Pedersen bases\n`);
        console.log(`📁 Saved to: ${OUTPUT_FILE}`);
        console.log(`📊 File size: ${fs.statSync(OUTPUT_FILE).size} bytes\n`);

    } catch (error) {
        console.error('❌ Error extracting bases:', error.message);
        process.exit(1);
    }
}

extractBases();
