"""
Check Both Main Ledger and Whisper Provider Sub-Account Balance

This script shows:
- Your main ledger account balance
- Your Whisper provider sub-account balance
- Pending refunds
- Account status

Prerequisites:
    pip install 0g-inference-sdk

Usage:
    export PRIVATE_KEY="0xYourPrivateKeyHere"
    python3 check_all_balances.py
"""

import os
import sys

from zerog_py_sdk import create_broker


PRIVATE_KEY = os.environ.get("PRIVATE_KEY", "")
NETWORK = "mainnet"

# 0G Whisper provider (speech-to-text)
WHISPER_PROVIDER = "0x36aCffCEa3CCe07cAdd1740Ad992dB16Ab324517"


def format_balance(wei_balance):
    """Convert Wei to 0G tokens (18 decimals)"""
    return wei_balance / 10**18


def main():
    if not PRIVATE_KEY:
        print("Error: Set PRIVATE_KEY environment variable")
        sys.exit(1)

    print("=" * 70)
    print("0G BALANCE CHECK - MAIN LEDGER + WHISPER PROVIDER")
    print("=" * 70)

    broker = create_broker(private_key=PRIVATE_KEY, network=NETWORK)
    address = broker.get_address()
    print(f"\n✓ Your Address: {address}")

    # ===== MAIN LEDGER BALANCE =====
    print("\n" + "=" * 70)
    print("MAIN LEDGER ACCOUNT BALANCE")
    print("=" * 70)
    main_balance_available = 0
    main_balance_locked = 0
    main_balance_total = 0
    
    try:
        ledger = broker.ledger.get_ledger()
        main_balance_available = ledger.balance
        main_balance_locked = ledger.locked
        main_balance_total = ledger.total_balance
        
        print(f"\n✓ Main Ledger Account Found!")
        print(f"  Total Balance:     {format_balance(main_balance_total):>12.6f} 0G")
        print(f"  Available:         {format_balance(main_balance_available):>12.6f} 0G")
        print(f"  Locked (in subs):  {format_balance(main_balance_locked):>12.6f} 0G")
    except Exception as e:
        print(f"\n✗ Main Ledger Account NOT FOUND")
        print(f"  Error: {type(e).__name__}")
        print(f"  You need to create it with: broker.ledger.add_ledger('amount')")

    # ===== WHISPER SUB-ACCOUNT BALANCE =====
    print("\n" + "=" * 70)
    print("WHISPER PROVIDER SUB-ACCOUNT BALANCE")
    print("=" * 70)
    print(f"\nProvider Address: {WHISPER_PROVIDER}")
    print(f"Service Type:     speech-to-text (Whisper)")
    
    whisper_balance = 0
    whisper_pending = 0
    
    try:
        sub_account, refunds = broker.inference.get_account_with_detail(WHISPER_PROVIDER)
        whisper_balance = sub_account.balance
        whisper_pending = sub_account.pending_refund
        
        print(f"\n✓ Whisper Sub-Account Found!")
        print(f"  Sub-Account Balance: {format_balance(whisper_balance):>12.6f} 0G")
        
        if whisper_pending > 0:
            print(f"  Pending Refund:      {format_balance(whisper_pending):>12.6f} 0G")
        else:
            print(f"  Pending Refund:      {format_balance(0):>12.6f} 0G (none)")
        
        if refunds:
            print(f"\n  Refund Details ({len(refunds)}):")
            for i, refund in enumerate(refunds, 1):
                amount = format_balance(refund.amount)
                lock_time = refund.remaining_lock_time
                print(f"    {i}. Amount: {amount:.6f} 0G")
                print(f"       Locked for: {lock_time}")
    except Exception as e:
        print(f"\n✗ Whisper Sub-Account NOT FOUND")
        print(f"  Error: {type(e).__name__}")
        print(f"  You need to transfer funds with:")
        print(f"    from zerog_py_sdk.utils import og_to_wei")
        print(f"    broker.ledger.transfer_fund('{WHISPER_PROVIDER}', 'inference', og_to_wei('1'))")

    # ===== SUMMARY =====
    print("\n" + "=" * 70)
    print("BALANCE SUMMARY")
    print("=" * 70)
    print(f"""
Main Account:
  Total:              {format_balance(main_balance_total):>12.6f} 0G
  Available:          {format_balance(main_balance_available):>12.6f} 0G
  Locked in subs:     {format_balance(main_balance_locked):>12.6f} 0G

Whisper Sub-Account:
  Balance:            {format_balance(whisper_balance):>12.6f} 0G
  Pending refund:     {format_balance(whisper_pending):>12.6f} 0G

Total Across All:     {format_balance(main_balance_total + whisper_balance):>12.6f} 0G
""")

    # ===== NEXT STEPS =====
    print("=" * 70)
    print("NEXT STEPS")
    print("=" * 70)
    
    if format_balance(main_balance_total) == 0:
        print("""
1. Create main ledger and deposit funds:
   broker.ledger.add_ledger('3')

2. Transfer to Whisper provider:
   from zerog_py_sdk.utils import og_to_wei
   broker.ledger.transfer_fund('0x36aCffCEa3CCe07cAdd1740Ad992dB16Ab324517', 
                               'inference', og_to_wei('1'))

3. Use Whisper service and check balance later
""")
    elif format_balance(whisper_balance) == 0:
        print("""
1. You have funds in main account but nothing in Whisper sub-account
   
2. Transfer to Whisper provider:
   from zerog_py_sdk.utils import og_to_wei
   broker.ledger.transfer_fund('0x36aCffCEa3CCe07cAdd1740Ad992dB16Ab324517', 
                               'inference', og_to_wei('1'))

3. Use Whisper service
""")
    else:
        print(f"""
✓ You're all set! You have:
  - Main account: {format_balance(main_balance_total):.6f} 0G
  - Whisper sub-account: {format_balance(whisper_balance):.6f} 0G

You can now use the Whisper provider for speech-to-text inference!
""")

    print("Done!\n")


if __name__ == "__main__":
    main()
