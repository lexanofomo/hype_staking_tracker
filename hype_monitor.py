import time
import json
import os
import requests
from datetime import datetime

WATCH_ADDRESSES = [
    "...", "...",
]

TG_BOT_TOKEN = "..."
TG_CHAT_ID = "-..."

POLL_INTERVAL = 30  # Seconds
STATE_FILE = "staking_monitor_state.json"
API_URL = "https://api.hyperliquid.xyz/info"

TRACK_STAKING = True  # Staking
TRACK_UNSTAKING = True  # Unstaking

def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TG_CHAT_ID, "text": message, "parse_mode": "HTML"}
        resp = requests.post(url, json=payload, timeout=5)
        if resp.status_code == 200:
            print("[TG] ✅ Sent")
        else:
            print(f"[TG] ❌ Error {resp.status_code}")
    except Exception as e:
        print(f"[TG] ❌ {e}")


def get_delegator_history(address):
    try:
        payload = {"type": "delegatorHistory", "user": address}
        resp = requests.post(API_URL, json=payload, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, list) else []
    except Exception as e:
        print(f"[API ERROR] {e}")
        return []


def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {}


def save_state(state):
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        print(f"[STATE ERROR] {e}")


def format_amount(amount_str):
    try:
        val = float(amount_str)
        if val >= 1_000_000:
            return f"{val / 1_000_000:,.2f}M"
        elif val >= 1_000:
            return f"{val / 1_000:,.2f}K"
        return f"{val:,.2f}"
    except:
        return str(amount_str)


def format_addr(addr):
    return f"{addr[:6]}...{addr[-4:]}" if len(addr) > 20 else addr


def process_monitoring():
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🔄 Checking...")

    state = load_state()

    for address in WATCH_ADDRESSES:
        print(f"  📍 {format_addr(address)}")

        history = get_delegator_history(address)

        if not history:
            print(f"     ⚠️  No delegation history")
            continue

        history.sort(key=lambda x: x.get('time', 0))

        if address not in state:
            state[address] = history[-1].get('time', 0)
            save_state(state)
            print(f"     ✅ Initialized")
            continue

        last_seen_time = state[address]

        new_events = [e for e in history if e.get('time', 0) > last_seen_time]

        if not new_events:
            print(f"     ✓ No new events")
            continue

        print(f"     🆕 {len(new_events)} new event(s)")

        for event in new_events:
            delta = event.get('delta', {})
            delegate = delta.get('delegate')

            if not delegate:
                continue

            is_undelegate = delegate.get('isUndelegate', False)
            amount = format_amount(delegate.get('amount', '0'))
            validator = delegate.get('validator', 'Unknown')
            event_time = event.get('time', 0)
            tx_hash = event.get('hash', 'NoHash')
            ts = datetime.fromtimestamp(event_time / 1000).strftime('%Y-%m-%d %H:%M:%S')

            if is_undelegate and TRACK_UNSTAKING:
                msg = (
                    f"Unstake\n"
                    f"Address: {address}\n"
                    f"Amount: {amount} HYPE\n"
                    f"Tx: https://hypurrscan.io/tx/{tx_hash}"
                )
                print(f"UNSTAKING: {amount}")
                send_telegram(msg)
                time.sleep(0.5)

            elif not is_undelegate and TRACK_STAKING:
                msg = (
                    f"Stake\n"
                    f"Address: {address}\n"
                    f"Amount: {amount} HYPE\n"
                    f"Tx: https://hypurrscan.io/tx/{tx_hash}"
                )
                print(f"STAKING: {amount}")
                send_telegram(msg)
                time.sleep(0.5)

        state[address] = history[-1].get('time', 0)
        save_state(state)


def test_telegram():
    msg = (
        f"✅ <b>Monitor Test</b>\n\n"
        f"Bot is working!\n"
        f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"Tracking:\n"
        f"{'✅' if TRACK_STAKING else '❌'} Staking\n"
        f"{'✅' if TRACK_UNSTAKING else '❌'} Unstaking\n\n"
        f"Wallets: {len(WATCH_ADDRESSES)}"
    )
    send_telegram(msg)


def show_history():
    print("\n📊 DELEGATION HISTORY:")
    print("=" * 70)

    for address in WATCH_ADDRESSES:
        print(f"\n📍 {address}")

        history = get_delegator_history(address)

        if not history:
            print("   ⚠️  No history found")
            continue

        history.sort(key=lambda x: x.get('time', 0), reverse=True)
        print(f"   Total: {len(history)} events\n")

        for i, event in enumerate(history[:10], 1):
            delta = event.get('delta', {})
            delegate = delta.get('delegate', {})

            is_undelegate = delegate.get('isUndelegate', False)
            amount = format_amount(delegate.get('amount', '0'))
            validator = delegate.get('validator', 'Unknown')
            event_time = event.get('time', 0)
            ts = datetime.fromtimestamp(event_time / 1000).strftime('%Y-%m-%d %H:%M')

            action = "🚨 UNSTAKE" if is_undelegate else "✅ STAKE"
            print(f"   {i:2d}. [{ts}] {action}: {amount} HYPE")
            print(f"       Validator: {format_addr(validator)}")

    print("\n" + "=" * 70)


def reset_state():
    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)
        print("✅ State reset")
    else:
        print("⚠️  No state file")


def main():
    print("\n" + "=" * 70)
    print("   🔍 HYPE STAKING MONITOR")
    print("=" * 70)
    print(f"\nWallets: {len(WATCH_ADDRESSES)}")
    for addr in WATCH_ADDRESSES:
        print(f"  • {addr}")
    print(f"\nSettings:")
    print(f"  • Poll: {POLL_INTERVAL}s")
    print(f"  • State: {STATE_FILE}")
    print(f"  • Track staking: {'YES ✅' if TRACK_STAKING else 'NO'}")
    print(f"  • Track unstaking: {'YES ✅' if TRACK_UNSTAKING else 'NO'}")
    print("=" * 70)

    print("\n📋 MENU:")
    print("  1. Start monitoring")
    print("  2. Test Telegram")
    print("  3. Show history")
    print("  4. Reset state")
    print("  5. Exit")

    choice = input("\n👉 Choose (1-5): ").strip()

    if choice == "2":
        test_telegram()
    elif choice == "3":
        show_history()
    elif choice == "4":
        reset_state()
    elif choice == "5":
        print("👋 Bye!")
    elif choice == "1":
        print("\n🚀 Starting monitor...\n")

        try:
            process_monitoring()
        except Exception as e:
            print(f"[ERROR] {e}")

        print("\n✅ Monitoring started. Press Ctrl+C to stop.\n")

        while True:
            try:
                time.sleep(POLL_INTERVAL)
                process_monitoring()
            except KeyboardInterrupt:
                print("\n\n⏹️  Stopped\n")
                break
            except Exception as e:
                print(f"[ERROR] {e}")
                time.sleep(30)
    else:
        print("❌ Invalid")


if __name__ == "__main__":
    main()