import json, requests, time
import rapidfuzz as rf

from pathlib import Path

class ItemManager():
    def __init__(self):
        self.database = Path("data\\WarframeMarketSellables.json").resolve()
        self.sellables_request = None

        # Startup processes
        self._request_market_sellables()
        self._build_db()
        
    def _request_market_sellables(self):
        r = requests.get("https://api.warframe.market/v2/items")
        data = r.json()
        self.sellables_request = data
    
    def _build_db(self):
        with open(self.database, 'w') as file:
            json.dump(self.sellables_request, file, indent=2)
            
        self.sellables_request = None
            
    def match_results(self, text: str) -> tuple[str, str]:
        with open(self.database, 'r') as file:
            data = json.load(file)
            

            # Faster search first
            timer_start = time.perf_counter()
            for item in data["data"]:
                try:
                    target_name = item["i18n"]["en"]["name"]
                    if target_name == text:
                        return (item["slug"], target_name.lower())
                except KeyError as e:
                    print(f"{item["slug"]} experienced {e}")
                
            timer_end = time.perf_counter()
            print(f"Exact match search took: {timer_end - timer_start}")
            
            # Slower check second
            timer_start = time.perf_counter()
            match_list = []
            for item in data["data"]:
                try:
                    target_name = item["i18n"]["en"]["name"]
                    ratio = rf.fuzz.ratio(text, target_name.lower())
                    
                    if text in target_name.lower():
                        ratio *= 1.2
                        if "set" in target_name.lower():
                            ratio *= 1.1
                        
                        ratio = min(100, ratio)
                        
                    if ratio >= 70:                            
                        match_list.append(
                            {
                                "target_name":target_name,
                                "slug":item["slug"],
                                "match_ratio":ratio
                            }
                        )
                        
                except KeyError as e:
                    print(f"{item["slug"]} experienced {e}")
                    
            timer_end = time.perf_counter()
            print(f"Fuzzy match search took: {timer_end - timer_start}")
                        
            perfect_matches = []
            if len(match_list) > 1:
                match_list = sorted(match_list, key=lambda x: x["match_ratio"])
                for item in match_list:
                    if item["match_ratio"] == 100:
                        perfect_matches.append(item)
                        
                # If more than one match has a score of 100
                if len(perfect_matches) > 1:
                    for match in perfect_matches:
                        score = 0
                        words = match["target_name"].split(" ")
                        for word in words:
                            if word.lower() in text:
                                score +=1
                        match["score"] = score
                    perfect_matches = sorted(perfect_matches, key=lambda x: x["score"])
                    return (perfect_matches[-1]["slug"], perfect_matches[-1]["target_name"])
                return (match_list[-1]["slug"], match_list[-1]["target_name"])
            elif len(match_list) == 1:
                return (match_list[0]["slug"], match_list[0]["target_name"])
            
        return ("no_match", "no_match")