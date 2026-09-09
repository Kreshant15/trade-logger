import os
import hmac
import hashlib
import time
import requests
from datetime import datetime, timedelta

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

API_KEY = os.getenv("DELTA_API_KEY")
API_SECRET = os.getenv("DELTA_API_SECRET")

BASE_URL = "https://api.delta.exchange"

def get_signature(api_secret, method, timestamp, path, query_string=''):
    signature_data = method + timestamp + path + query_string
    return hmac.new(api_secret.encode('utf-8'), signature_data.encode('utf-8'), hashlib.sha256).hexdigest()

def make_request(endpoint, method="GET", query_string=""):
    timestamp = str(int(time.time()))
    signature = get_signature(API_SECRET, method, timestamp, endpoint, query_string)
    
    headers = {
        "api-key": API_KEY,
        "timestamp": timestamp,
        "signature": signature,
        "User-Agent": "TradeLogger/1.0"
    }
    
    url = f"{BASE_URL}{endpoint}"
    if query_string:
        url += f"?{query_string}"
        
    return requests.request(method, url, headers=headers).json()

def main():
    if not API_KEY or not API_SECRET:
        print("⚠️ Delta API Key or Secret missing from environment variables.")
        return

    try:
        # 1. Fetch USDT Balance
        balance_res = make_request("/v2/wallet/balances")
        usdt_balance = 0.0
        
        if balance_res.get("success"):
            for asset in balance_res.get("result", []):
                if asset.get("asset_symbol") == "USDT":
                    usdt_balance = float(asset.get("balance", 0))
                    break

        # 2. Fetch Recent Fills (Trades)
        fills_res = make_request("/v2/fills", query_string="page_size=100")
        
        trades_24h = 0
        fees_24h = 0.0
        
        if fills_res.get("success"):
            yesterday = datetime.utcnow() - timedelta(days=1)
            for fill in fills_res.get("result", []):
                fill_time = datetime.utcfromtimestamp(fill['created_at'] / 1000000.0)
                if fill_time > yesterday:
                    trades_24h += 1
                    fees_24h += float(fill.get("fee", 0))

        final_message = (
            "📊 **Daily Delta Exchange Summary** 📊\n\n"
            f"💰 USDT Balance: `${usdt_balance:.2f}`\n"
            f"🔄 Trades (24h): `{trades_24h}`\n"
            f"💸 Fees Paid (24h): `${fees_24h:.4f}`"
        )
        
        # Dispatch to Discord
        if DISCORD_WEBHOOK_URL:
            requests.post(DISCORD_WEBHOOK_URL, json={"content": final_message})
            print("Webhook sent successfully.")
        else:
            print(final_message)
            
    except Exception as e:
        print(f"❌ Error fetching account data: {str(e)}")

if __name__ == "__main__":
    main()