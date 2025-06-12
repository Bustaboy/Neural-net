# market/dominance.py
import requests

class BTCDominanceTracker:
    def get_btc_dominance(self) -> float:
        # Placeholder: Fetch from CoinGecko or similar
        response = requests.get("https://api.coingecko.com/api/v3/global")
        data = response.json()
        return data['data']['market_cap_percentage']['btc']
