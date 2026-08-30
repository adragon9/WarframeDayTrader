from PyQt6.QtCore import pyqtBoundSignal, QStringConverter 
from PyQt6.QtWidgets import (
    QLineEdit
)
from typing import Literal

import requests, json, os, statistics
import datetime as dt
import scripts.SellablesManager

class PriceRecommender():
    def __init__(self, main_messenger: pyqtBoundSignal, sub_messenger: pyqtBoundSignal):
        self.main_messenger = main_messenger
        self.sub_messenger = sub_messenger
    
    def _process_searchTerm(self, text: str, searcher: scripts.SellablesManager.ItemManager):
        """ 
        Process input text to reduce problems
        """
        text = text.strip()
        text = text.replace("&", "and")
        text = text.lower()
        slug, name = searcher.match_results(text)
    
        return slug, name
    
    def _create_url(self, text:str, type: Literal["orders"] = "orders") -> str:
        if type == "orders":
            return f"https://api.warframe.market/v2/orders/item/{text}"
    
    def _get_request(self, url:str):
        try:
            r = requests.get(url)
            return r.json()
        except Exception as e: 
            print(e)
            return {}
    
    def _process_pricing_data(self, data: dict):            
        seller_data = []
        buyer_data = []
        date_format = "%Y-%m-%d %H:%M:%S"
        now = dt.datetime.strptime(dt.datetime.strftime(dt.datetime.now(), date_format), date_format)
        try:
            for obj in data["data"]:
                update_time = dt.datetime.strptime(obj["updatedAt"].replace("Z", "").replace("T", " "), date_format)
                days_since = (now - update_time).days
                
                if days_since > 2 and obj["user"]["status"] != "ingame":
                    continue
                
                elif obj["user"]["status"] != "ingame":
                    continue
                
                elif obj["type"] == "buy":
                    buyer_data.append({
                        "buyer":obj["user"]["ingameName"],
                        "reputation":obj["user"]["reputation"],
                        "itemQuantity":obj["quantity"],
                        "buyPrice":obj["platinum"]
                    })
                elif obj["type"] == "sell":
                    seller_data.append({
                        "seller":obj["user"]["ingameName"],
                        "reputation":obj["user"]["reputation"],
                        "itemQuantity":obj["quantity"],
                        "salePrice":obj["platinum"]
                    })
                    
            return (seller_data, buyer_data)
        
        except (TypeError, KeyError) as e:
            print(str(e))
            return [], []

    def _cull_prices(self, prices: list, mode: float|int, std_dev: float|int):
        # Dynamic deviation adjustment
        if len(prices) < 10:
            std_dev_mod = std_dev
        if len(prices) < 100:
            std_dev_mod = std_dev * 2
        else:
            std_dev_mod = std_dev * 3
        
        # Cull outliers
        for cost in prices[:]:
            if cost > mode + std_dev_mod:
                prices.remove(cost)
            elif cost < mode - std_dev_mod:
                prices.remove(cost)

        return prices
    
    def _process_pricing_recommendations(self, searchTerm: str, url: str, slug: str, seller_data: list, buyer_data: list):
        if not seller_data and not buyer_data:
            if not searchTerm:
                return f"<h3>Error, no search term was entered!" 
            else:
                return f"<h3>Error, there was a problem retrieving the data for <i>{searchTerm}</i></h3>" 
        
        result = (f"<h2>Searched for:"
                  f" <a href='https://warframe.market/items/{slug}'>{searchTerm}</a></h2>")
        
        seller_data = sorted(seller_data, key=lambda x: x["salePrice"])
        buyer_data = sorted(buyer_data, key=lambda x: x["buyPrice"])
                
        # Collect general data
        sale_prices = []
        if seller_data != []:
            for seller in seller_data:
                sale_prices.append(seller["salePrice"])
            
        purchase_prices = []
        if buyer_data != []:
            for buyer in buyer_data:
                purchase_prices.append(buyer["buyPrice"])
        
        # Gather stats (SELLERS)
        if len(sale_prices) > 1:
            average_cost = statistics.mean(sale_prices)
            median = statistics.median(sale_prices)
            mode = statistics.multimode(sale_prices)
            std_dev = statistics.stdev(sale_prices)
            sale_prices = self._cull_prices(sale_prices, mode=mode[0], std_dev=std_dev)
        elif len(sale_prices) == 1:
            average_cost = purchase_prices[0]
            median = purchase_prices[0]
            mode = purchase_prices[0]
            std_dev = 0
        else:
            result += f"<h1>NO SALE DATA</h1>"
            return result
        
        # Gather stats (BUYERS)
        average_cost_b = "No buyers"
        median_b = "No buyers"
        mode_b = "No buyers"
        if len(purchase_prices) > 1:
            average_cost_b = statistics.mean(purchase_prices)
            median_b = statistics.median(purchase_prices)
            mode_b = statistics.multimode(purchase_prices)
        elif len(purchase_prices) == 1:
            average_cost_b = purchase_prices[0]
            median_b = purchase_prices[0]
            mode_b = purchase_prices[0]
        

        
        # Re-average culled list
        average_cost = statistics.mean(sale_prices)
        
        # Recommended price
        # It's just the (lowest most common price - 1)
        recommendation = mode[0] - 1
        
        if type(average_cost_b) == float:
            round(average_cost_b) 
        
        if purchase_prices != []:
            top_buyer = purchase_prices[-1]
        else:
            top_buyer = "No buyers"
        
        # Results
        # Price recommendations
        result +=f"<h1>Pricing Recommendations</h1>"
        result +=f"The most common sale price is <span style='color:#add8e6'>{mode[0]}p.</span><br>"
        result +=f"To attempt to balance profit and sell speed try <span style='color:#add8e6'>{recommendation}p</span>.<br>"
        result +=f"Average fair price is <span style='color:#add8e6'>{round(average_cost)}p</span>, though, you may sell slowly if you do this.<br>"
        result +=f"To match the lowest seller sell for <span style='color:#add8e6'>{sale_prices[0]}p</span>.<br>"
        result +=f"To <span style='color:#c64c4c'><b>outsell</b></span> the lowest seller sell for <span style='color:#add8e6'>{sale_prices[0]-1}p</span>.<span style='color:#c64c4c'><b>(NOT RECOMMENDED)</b></span><br>"
        
        if top_buyer != "No buyers" and abs(recommendation - top_buyer) < 5:
            result += f"You should consider fulfilling the top buy order of <span style='color:#add8e6'>{top_buyer}p</span>, it is only <span style='color:#add8e6'>{abs(recommendation - top_buyer)}p</span> away from what is being recommended. This will be the quickest sale."
                
        result += "<hr>"
        
        # Notices
        result += "<h1>Notices</h1>"
        result += "<h2><span style='color:#c64c4c'>Remember, warframe.market is <b>extremely</b> prone to price wars!</span></h2>"
        result += "<h3><span style='color:#c64c4c'>This means if you sell lower than the lowest seller someone will likely try to one up you causing a collapse in pricing.</span></h3>"
        
        if purchase_prices and sale_prices[0] == purchase_prices[-1]:
            result += (f"The highest buyer matches the lowest seller (<span style='color:#add8e6'>{sale_prices[0]}p</span>),"
                       f" recommendation for immediate sale is to sell to the highest buyer.<br>")
        elif purchase_prices and sale_prices:
            distance = abs(sale_prices[0] - purchase_prices[-1])
            result += (f"The highest buyer and lowest seller are <span style='color:#add8e6'>{distance}p</span> apart.<br>"
                       f" The highest <u>buyer</u> is at <span style='color:#add8e6'>{purchase_prices[-1]}p</span>"
                       f" and the lowest <u>seller</u> is at <span style='color:#add8e6'>{sale_prices[0]}p</span>.<br>")
        else:
            result += "<h2>No Notices</h2>"
            
        result += "<hr>"
        
        # Detailed results
        result += (
            f"<h1>Seller Data</h1>"
            f"Average: {round(average_cost)}<br>"
            f"Median: {median}<br>"
            f"Mode: {mode}<br>"
            f"Lowest Seller: {sale_prices[0]}<br>"
            f"<hr>"
            f"<h1>Buyer Data</h1>"
            f"Average: {average_cost_b}<br>"
            f"Median: {median_b}<br>"
            f"Mode: {mode_b}<br>"
            f"Top Buyer: {top_buyer}<br>"
            f"<hr>"
        )
        
        if seller_data:
            lowest_seller_data = seller_data[0]
            result += "<h1>Lowest Seller</h1>"
            for key in lowest_seller_data.keys():
                if key == "seller":
                    result+=f"{key}: <span style='color:#c64c4c'>{lowest_seller_data[key]}</span><br>"
                else:
                    result+=f"{key}: {lowest_seller_data[key]}<br>"
        
        
        if buyer_data:
            highest_buyer_data = buyer_data[-1]
            result+="<h1>Highest Buyer</h1>"
            for key in highest_buyer_data.keys():
                if key == "buyer":
                    result+=f"{key}: <span style='color:#c64c4c'>{highest_buyer_data[key]}</span><br>"
                else:
                    result+=f"{key}: {highest_buyer_data[key]}<br>"
        
        return result
        
    def run(self, input:QLineEdit):
        searcher = scripts.SellablesManager.ItemManager()
        searchTerm = input.text()
        input.clear()       
        
        slug, name = self._process_searchTerm(searchTerm, searcher)
        url = self._create_url(slug)
        response = self._get_request(url)
        seller_data, buyer_data = self._process_pricing_data(response)
        result_str = self._process_pricing_recommendations(name, url, slug, seller_data, buyer_data)
        
        self.main_messenger.emit(result_str)
        