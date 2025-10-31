import { Indexer, ZgFile } from '@0glabs/0g-ts-sdk';
import { Wallet, JsonRpcProvider } from 'ethers';
import * as fs from 'fs';

// Configuration for mainnet
const PRIVATE_KEY = process.env.PRIVATE_KEY || '0xc5509a5827e17a1cd286d85d5084bb8fdb37112cee4f7683508bd2ed422916fe';
const RPC_URL = 'https://evmrpc.0g.ai';
const INDEXER_URL = 'https://indexer-storage-turbo.0g.ai';

async function testUpload() {
  console.log('\n' + '='.repeat(70));
  console.log('  0G STORAGE - TYPESCRIPT SDK TEST (MAINNET)');
  console.log('='.repeat(70));

  try {
    // Setup provider and signer
    const provider = new JsonRpcProvider(RPC_URL);
    const wallet = new Wallet(PRIVATE_KEY, provider);

    console.log(`\n✅ Account: ${wallet.address}`);

    // Check balance
    const balance = await provider.getBalance(wallet.address);
    console.log(`   Balance: ${parseFloat(balance.toString()) / 1e18} ETH`);

    // Create test file
    console.log(`\n📝 Creating test file...`);
    const testContent = 'TypeScript SDK test file for mainnet upload\n';
    const testFile = './ts_test.txt';
    fs.writeFileSync(testFile, testContent);
    console.log(`   File: ${testFile}`);
    console.log(`   Size: ${testContent.length} bytes`);

    // Create ZgFile from path
    console.log(`\n🔧 Creating ZgFile...`);
    const file = await ZgFile.fromFilePath(testFile);

    // Generate merkle tree
    console.log(`🌳 Generating Merkle tree...`);
    const [tree, treeErr] = await file.merkleTree();
    if (treeErr) {
      throw new Error(`Merkle tree generation failed: ${treeErr}`);
    }
    console.log(`   Root Hash: ${tree.rootHash()}`);

    // Create Indexer
    console.log(`\n🔧 Initializing Indexer...`);
    console.log(`   Indexer: ${INDEXER_URL}`);
    const indexer = new Indexer(INDEXER_URL);

    // Upload with options
    console.log(`\n📤 Uploading to 0G Storage...`);
    console.log(`   Network: ${RPC_URL}`);

    const uploadOptions = {
      tags: new Uint8Array([0]),
      finalityRequired: true,
      taskSize: 10,
      expectedReplica: 1,
      skipTx: false,
    };

    try {
      console.log(`   Starting upload...`);
      const result = await indexer.upload(
        file,
        RPC_URL,
        wallet,
        uploadOptions
      );

      console.log(`\n` + '='.repeat(70));
      console.log('  ✅ UPLOAD SUCCESSFUL!');
      console.log('='.repeat(70));
      console.log(`\n📋 Transaction Details:`);
      console.log(`   Transaction Hash: ${result.transactionHash}`);
      console.log(`   Root Hash:        ${result.rootHash}`);

      console.log(`\n🔗 View on Explorer:`);
      console.log(`   https://chainscan.0g.ai/tx/${result.transactionHash}`);

    } catch (uploadError) {
      console.log(`\n❌ Upload failed:`);
      console.log(`   Error type: ${uploadError.constructor.name}`);
      console.log(`   Error message: ${uploadError.message}`);

      // Try to extract more details
      if (uploadError.code) {
        console.log(`   Code: ${uploadError.code}`);
      }
      if (uploadError.reason) {
        console.log(`   Reason: ${uploadError.reason}`);
      }
      if (uploadError.transaction) {
        console.log(`   Transaction hash: ${uploadError.transaction.hash}`);
      }

      // Show error details
      console.log(`\n   Details:`);
      console.log(`   ${JSON.stringify({
        code: uploadError.code,
        reason: uploadError.reason,
        transaction: uploadError.transaction?.hash,
        action: uploadError.action,
      }, null, 2)}`);
    }

    // Cleanup
    await file.close();
    fs.unlinkSync(testFile);

  } catch (error) {
    console.log(`\n❌ ERROR: ${error.message}`);
    console.log(`   Stack: ${error.stack.substring(0, 500)}`);
  }
}

testUpload();
