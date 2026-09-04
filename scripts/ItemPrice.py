from PyQt6.QtCore import pyqtBoundSignal
from PyQt6.QtWidgets import (
    QLineEdit
)
from typing import Literal

import requests, statistics, regex
import datetime as dt
import scripts.SellablesManager

import time

class PriceRecommender():
    def __init__(self, main_messenger: pyqtBoundSignal, sub_messenger: pyqtBoundSignal, line_edit: QLineEdit):
        self.main_messenger = main_messenger
        self.sub_messenger = sub_messenger
        self.line_edit = line_edit
    
    def _process_searchTerm(self, text: str, searcher: scripts.SellablesManager.ItemManager):
        self.sub_messenger.emit("Processing search term...")
        """ 
        Process input text to reduce problems
        """
        text = text.strip()
        text = text.replace("&", "and")
        text = text.lower()
        slug, name = searcher.match_results(text)
    
        return slug, name
    
    def _create_url(self, text:str, type: Literal["orders", "sets"] = "orders") -> str:
        self.sub_messenger.emit("Creating url...")
        if type == "orders":
            return f"https://api.warframe.market/v2/orders/item/{text}"
        elif type == "sets":
            return f"https://api.warframe.market/v2/item/{text}/set"
        else:
            return ""
    
    def _get_request(self, url:str):
        self.sub_messenger.emit("Getting api request...")
        try:
            r = requests.get(url)
            return r.json()
        except Exception as e: 
            print(e)
            return {}
    
    def _process_data(self, data: dict, ignore_date = False):        
        self.sub_messenger.emit("Processing pricing data...")    
        seller_data = []
        buyer_data = []
        date_format = "%Y-%m-%d %H:%M:%S"
        now = dt.datetime.strptime(dt.datetime.strftime(dt.datetime.now(), date_format), date_format)
        try:
            for obj in data["data"]:
                update_time = dt.datetime.strptime(obj["updatedAt"].replace("Z", "").replace("T", " "), date_format)
                days_since = (now - update_time).days
                
                if days_since > 2 and obj["user"]["status"] != "ingame" and not ignore_date:
                    continue
                
                elif obj["user"]["status"] != "ingame":
                    continue
                
                elif obj["type"] == "buy":
                    for _ in range(obj["quantity"]):
                        try:
                            buyer_data.append({
                                "buyer":obj["user"]["ingameName"],
                                "reputation":obj["user"]["reputation"],
                                "itemQuantity":obj["quantity"],
                                "buyPrice":obj["platinum"],
                                "quantityInSet":obj["quantityInSet"]
                            })
                        except KeyError:
                            buyer_data.append({
                                "buyer":obj["user"]["ingameName"],
                                "reputation":obj["user"]["reputation"],
                                "itemQuantity":obj["quantity"],
                                "buyPrice":obj["platinum"]
                            })
                elif obj["type"] == "sell":
                    for _ in range(obj["quantity"]):
                        try:
                            seller_data.append({
                                "seller":obj["user"]["ingameName"],
                                "reputation":obj["user"]["reputation"],
                                "itemQuantity":obj["quantity"],
                                "salePrice":obj["platinum"],
                                "quantityInSet":obj["quantityInSet"]
                            })
                        except KeyError:
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

    def _sum_of_parts(self, set_data:dict):
        result = 0
        for item in set_data["data"]["items"]:
            if not regex.match(r"\w*_\w*_set", item["slug"]):
                self.sub_messenger.emit(f"Getting {item["i18n"]["en"]["name"]}'s minimum price...")    
                item_url = self._create_url(item["slug"])
                item_orders = self._get_request(item_url)
                seller_data, buyer_data = self._process_data(item_orders, ignore_date=True)
                seller_data = sorted(seller_data, key=lambda x: x["salePrice"])
                try:
                    logged_seller = {}
                    for i in range(item["quantityInSet"]):
                        if seller_data[i]["itemQuantity"] >= item["quantityInSet"] and not logged_seller:
                            result += seller_data[0]["salePrice"] * item["quantityInSet"]
                            break
                        else:
                            result += seller_data[i]["salePrice"]
                            logged_seller = seller_data
                except KeyError:
                    print(seller_data)
                time.sleep(.5)
        return result
        
    def _cull_prices(self, prices: list, mode: float|int, std_dev: float|int):
        self.sub_messenger.emit("Culling outlier prices...")
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

        return prices
    
    def _process_pricing_recommendations(self, searchTerm: str, url: str, slug: str, seller_data: list, buyer_data: list, part_sum: int|float = 0):
        self.sub_messenger.emit(f"Generating recommendations...")  
        if not seller_data and not buyer_data:
            if not searchTerm:
                return f"<h3>Error, no search term was entered!" 
            else:
                return f"<h3>Error, there was a problem retrieving the data for <i>{searchTerm}</i></h3>" 
        elif not seller_data:
            return f"<h3>Error, there is no seller data for this item.</h3><br><h3>Please try again later.</h3>"

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
            mode = statistics.multimode(sale_prices)
            std_dev = statistics.stdev(sale_prices)
            sale_prices = self._cull_prices(sale_prices, mode=mode[0], std_dev=std_dev)
            average_cost = statistics.mean(sale_prices)
            median = statistics.median(sale_prices)
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
        # Notices
        result += "<h2><span style='color:#c64c4c'>Remember, warframe.market is <b>extremely</b> prone to price wars!</span></h2>"
        result += "<h3><span style='color:#c64c4c'>This means if you sell lower than the lowest seller someone will likely try to one up you causing a collapse in pricing.</span></h3>"
        
        if purchase_prices and sale_prices[0] == purchase_prices[-1]:
            result += (f"<p>The highest buyer matches the lowest seller (<span style='color:#add8e6'>{sale_prices[0]}p</span>),"
                       f" recommendation for immediate sale is to sell to the highest buyer.<br></p>") 
        elif purchase_prices and sale_prices:
            distance = abs(sale_prices[0] - purchase_prices[-1])
            result += (f"The highest buyer and lowest seller are <span style='color:#add8e6'>{distance}p</span> apart.<br>"
                       f" The highest <u>buyer</u> is at <span style='color:#add8e6'>{purchase_prices[-1]}p</span>"
                       f" and the lowest <u>seller</u> is at <span style='color:#add8e6'>{sale_prices[0]}p</span>.")            
        try:
            highest_buy = purchase_prices[-1]
        except IndexError:
            highest_buy = 0
        
        buy_recommendation = max(highest_buy, (round((sale_prices[0]-1)*.85)))
        fast_profit_margin = sale_prices[0] - buy_recommendation
        
        # Price recommendations
        result +=f"<h1>Pricing Recommendations</h1>"
        if top_buyer != "No buyers" and abs(recommendation - top_buyer) <= 5:
            result += f"You should consider fulfilling the top buy order of <span style='color:#add8e6'>{top_buyer}p</span>, it is only <span style='color:#add8e6'>{abs(recommendation - top_buyer)}p</span> away from what is being recommended. This will be the quickest sale."
        result +=f"<table>"
        result +=f"<tr>"
        result += "<td class='col-1'></td>"
        result +=f"<td class='col-2'>Platinum</td>"
        result +=f"</tr>"
        result +=f"<tr>"
        result +=f"<td colspan='2'><b>Info</b></td>"
        result +=f"</tr>"
        result +=f"<tr>"
        result +=f"<td class='col-1'>Average Price (Adjusted)</td>"
        result +=f"<td class='col-2'><span style='color:#add8e6'>{round(average_cost)}p</span></td>"
        result +=f"</tr>"
        result +=f"<tr>"
        result +=f"<td class='col-1'>Most Common Price</td>"
        result +=f"<td class='col-2'><span style='color:#add8e6'>{mode[0]}p</span></td>"
        result +=f"</tr>"
        if part_sum != 0:
            result +=f"<tr>"
            result +=f"<td class='col-1'>Sum of Set Parts</td>"
            result +=f"<td class='col-2'><span style='color:#add8e6'>{part_sum}p</span></td>"
            result +=f"</tr>"
        result +=f"<tr>"
        result +=f"<td class='col-1'>Highest Buy Order</td>"
        result +=f"<td class='col-2'><span style='color:#add8e6'>{highest_buy}p</span></td>"
        result +=f"</tr>"
        result +=f"<tr>"
        result +=f"<td colspan='2'><b><a href='https://warframe.market/items/{slug}?type=sell'>Sale Recommendations</a></b></td>"
        result +=f"</tr>"
        result +=f"<tr>"
        result +=f"<td class='col-1'>Balanced Offer</td>"
        result +=f"<td class='col-2'><span style='color:#add8e6'>{recommendation}p</span></td>"
        result +=f"</tr>" 
        result +=f"<tr>"
        result +=f"<td class='col-1'>Match Lowest</td>"
        result +=f"<td class='col-2'><span style='color:#add8e6'>{sale_prices[0]}p</span></td>"
        result +=f"</tr>" 
        result +=f"<tr>"
        result +=f"<td class='col-1'>Beat Lowest <span style='color:#c64c4c'><b>(Not Recommended)</span></td>"
        result +=f"<td class='col-2'><span style='color:#add8e6'>{sale_prices[0]-1}p</span></td>"
        result +=f"</tr>" 
        result +=f"<tr>"
        result +=f"<td colspan=2><b><a href='https://warframe.market/items/{slug}?type=buy'>Purchase Recommendations</a></b></td>"
        result +=f"</tr>"
        result +=f"<tr>"
        result +=f"<td class='col-1'>Good Buy Estimate</td>"
        result +=f"<td class='col-2'><span style='color:#add8e6'>{buy_recommendation}p</span></td>"
        result +=f"</tr>"
        if fast_profit_margin == 0:
            result +=f"<tr>"
            result +=f"<td class='col-1'>Profit Selling at the Current Lowest Price</td>"
            result +=f"<td class='col-2'>Break Even</td>"
            result +=f"</tr>"
        elif fast_profit_margin < 0:
            result +=f"<tr>"
            result +=f"<td class='col-1'>Profit Selling at the Current Lowest Price</td>"
            result +=f"<td class='col-2'><span style='color:#c64c4c'>Loss Likely</span></td>"
            result +=f"</tr>"
        else:
            result +=f"<tr>"
            result +=f"<td class='col-1'>Profit Selling at the Current Lowest Price</td>"
            result +=f"<td class='col-2'><span style='color:#add8e6'>{fast_profit_margin}p</span></td>"
            result +=f"</tr>"
        result +=f"</table>"
                        
        # Detailed results
        result +=f"<h1>Details</h1>"
        result += (
            f"<table>"
            f"<tr>"
            f"<td colspan='2' style='background:#4c4c4c;'><b>Seller Data</b></td>"
            f"</tr>"
            f"<tr>"
            f"<td class='col-1'>Average</td>"
            f"<td>{round(average_cost)}</td>"
            f"</tr>"
            f"<tr>"
            f"<td class='col-1'>Median</td>"
            f"<td>{median}</td>"
            f"</tr>"
            f"<tr>"
            f"<td class='col-1'>Mode</td>"
            f"<td>{mode}</td>"
            f"</tr>"
            f"<tr>"
            f"<td class='col-1'>Lowest Seller</td>"
            f"<td>{sale_prices[0]}</td>"
            f"</tr>"
            f"<tr>"
            f"<td colspan='2' style='background:#4c4c4c;'><b>Buyer Data</b></td>"
            f"</tr>"
            f"<tr>"
            f"<td class='col-1'>Average</td>"
            f"<td>{average_cost_b}</td>"
            f"</tr>"
            f"<tr>"
            f"<td class='col-1'>Median</td>"
            f"<td>{median_b}</td>"
            f"</tr>"
            f"<tr>"
            f"<td class='col-1'>Mode</td>"
            f"<td>{mode_b}</td>"
            f"</tr>"
            f"<tr>"
            f"<td class='col-1'>Highest Buyer</td>"
            f"<td>{top_buyer}</td>"
            f"</tr>"
            f"</table>"
        )
        
        result += "<h1>Top Buyer & Seller</h1>"
        result +=f"<table>"
        if seller_data:
            lowest_seller_data = seller_data[0]
            result +=f"<tr><td colspan='2' style='background:#4c4c4c;'><b>Lowest Seller</b></td></tr>"
            for key in lowest_seller_data.keys():
                if key == "seller":
                    result+=f"<tr>"
                    result+=f"<td class='col-1'>{key}</td>"
                    result+=f"<td><span style='color:#c64c4c'>{lowest_seller_data[key]}</span></td>"
                    result+=f"</tr>"
                else:
                    result+=f"<tr>"
                    result+=f"<td class='col-1'>{key}</td>"
                    result+=f"<td>{lowest_seller_data[key]}</td>"
                    result+=f"</tr>"

        if buyer_data:
            highest_buyer_data = buyer_data[-1]
            result +=f"<tr><td colspan='2' style='background:#4c4c4c;'><b>Top Buyer</b></td></tr>"
            for key in highest_buyer_data.keys():
                if key == "buyer":
                    result+=f"<tr>"
                    result+=f"<td class='col-1'>{key}</td>"
                    result+=f"<td><span style='color:#c64c4c'>{highest_buyer_data[key]}</span></td>"
                    result+=f"</tr>"
                else:
                    result+=f"<tr>"
                    result+=f"<td class='col-1'>{key}</td>"
                    result+=f"<td>{highest_buyer_data[key]}</td>"
                    result+=f"</tr>"
                    
        result +=f"</table>"
        
        return result
        
    def run(self):
        user_input = self.line_edit
        searcher = scripts.SellablesManager.ItemManager()
        searchTerm = user_input.text()
        part_sum = 0
        user_input.clear()
        
        self.sub_messenger.emit("Starting")
        slug, name = self._process_searchTerm(searchTerm, searcher)
        if regex.match(r"\w*_\w*_set", slug):
            set_url = self._create_url(slug, "sets")
            set_data = self._get_request(set_url)
            part_sum = self._sum_of_parts(set_data)
        url = self._create_url(slug)
        response = self._get_request(url)
        seller_data, buyer_data = self._process_data(response, ignore_date=True)
        if part_sum != 0:
            result_str = self._process_pricing_recommendations(name, url, slug, seller_data, buyer_data, part_sum)
        else:
            result_str = self._process_pricing_recommendations(name, url, slug, seller_data, buyer_data)
        
        self.main_messenger.emit(result_str)
        