import requests, json, os, statistics
import datetime as dt
from tkinter import messagebox

def get(request_header):
    r = requests.get(f'https://api.warframe.market/v2/{request_header}')
    with open('item_posts.json', 'w', encoding='utf-8') as file:
        json.dump(r.json(), file, indent=4)

def get_platinum_costs() -> tuple[list, list]:
    if os.path.exists('item_posts.json'):
        with open('item_posts.json', 'r', encoding='utf-8') as file:
            data = json.load(file)
        
        seller_data = []
        buyer_data = []
        date_format = "%Y-%m-%d %H:%M:%S"
        now = dt.datetime.strptime(dt.datetime.strftime(dt.datetime.now(), date_format), date_format)
        for obj in data["data"]:
            update_time = dt.datetime.strptime(obj["updatedAt"].replace("Z", "").replace("T", " "), date_format)
            days_since = (now - update_time).days
            if days_since > 2:
                pass
            elif obj["user"]["status"] != "ingame":
                pass
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
    else:
        return ([], [])

def price_suggestion(seller_data:list, buyer_data:list):
    # Temp
    current_rep = 0
    if current_rep < 1000:
        discount = (.0001 * current_rep) + .9
    else:
        discount = 1
    
    seller_data = sorted(seller_data, key=lambda x: x["salePrice"])
    buyer_data = sorted(buyer_data, key=lambda x: x["buyPrice"])
    
    # Collect general data
    sale_prices = []
    for seller in seller_data:
        sale_prices.append(seller["salePrice"])
    
    purchase_prices = []
    if buyer_data != []:
        for buyer in buyer_data:
            purchase_prices.append(buyer["buyPrice"])
        
    # Sort list least -> greatest
    sale_prices.sort()
    
    # Gather stats (SELLERS)
    average_cost = statistics.mean(sale_prices)
    median = statistics.median(sale_prices)
    mode = statistics.multimode(sale_prices)
    std_dev = statistics.stdev(sale_prices)
    
    # Gather stats (BUYERS)
    average_cost_b = "No buyers"
    median_b = "No buyers"
    mode_b = "No buyers"
    if purchase_prices != []:
        average_cost_b = statistics.mean(purchase_prices)
        median_b = statistics.median(purchase_prices)
        mode_b = statistics.multimode(purchase_prices)
    
    # Dynamic deviation adjustment
    if len(sale_prices) < 10:
        std_dev_mod = std_dev
    if len(sale_prices) < 30:
        std_dev_mod = std_dev * 2
    else:
        std_dev_mod = std_dev * 3
    
    # Cull outliers
    for cost in sale_prices[:]:
        if cost > average_cost + std_dev_mod:
            print(f"Removing: {cost}\nReason: Too High\n")
            sale_prices.remove(cost)
        elif cost < average_cost - std_dev_mod:
            print(f"Removing: {cost}\nReason: Too Low\n")
            sale_prices.remove(cost)
    
    # Re-average culled list
    average_cost = statistics.mean(sale_prices)
    
    # Recommended price
    recommendation = round(average_cost - (average_cost * (1 - discount)))
    if recommendation < sale_prices[0]:
        recommendation = sale_prices[0]
    
    if type(average_cost_b) == float:
        round(average_cost_b) 
    
    if purchase_prices != []:
        top_buyer = purchase_prices[-1]
    else:
        top_buyer = "No buyers"
    
    # Results
    result = (
          f"[[ Seller Data ]]\n"
          f"Average: {round(average_cost)}\n"
          f"Median: {median}\n"
          f"Mode: {mode}\n"
          f"Standard Deviation: {std_dev}\n"
          f"Modded Standard Deviation: {std_dev_mod}\n"
          f"Lowest Seller: {sale_prices[0]}\n"
          f"\n[[ Buyer Data ]]\n"
          f"Average: {average_cost_b}\n"
          f"Median: {median_b}\n"
          f"Mode: {mode_b}\n"
          f"Top Buyer: {top_buyer}\n"
        )
    

    
    print(result)
    
    # Notices
    if purchase_prices and sale_prices[0] == purchase_prices[-1]:
        print(f"The highest buyer matches the lowest seller ({sale_prices[0]}p), recommendation for immediate sale is to sell to the highest buyer.")
    elif purchase_prices and abs(sale_prices[0] - purchase_prices[-1]) <= 5:
        print(f"NOTICE: The highest buyer and lowest seller are within 5 of eachother the highest buyer is at {purchase_prices[-1]}p and the lowest seller is at {sale_prices[0]}p.\n")
    
    print() # seperator
    
    if seller_data:
        lowest_seller_data = seller_data[0]
        print("Lowest Seller:")
        for key in lowest_seller_data.keys():
            print(f"{key}: {lowest_seller_data[key]}")
    
    print() # seperator
    
    if buyer_data:
        highest_buyer_data = buyer_data[0]
        print("Highest Buyer:")
        for key in highest_buyer_data.keys():
            print(f"{key}: {highest_buyer_data[key]}")

    print() # seperator
    
    print(f"To outsell the lowest seller: {sale_prices[0]-1}p")
    print(f"Balance profit and sell speed: {recommendation}p")
    print(f"Average fair price: {round(average_cost)}p")
        

        
if __name__ == "__main__":
    new_request = messagebox.askyesno("Confirm", "Would you like to search a new term?")
    if new_request:
        while new_request:
            request_header = f"orders/item/{input("enter item slug:")}"
            request_header = request_header.replace(" ", "_").strip().lower()
            if "&" in request_header:
                request_header = request_header.replace("&", "and")
            get(request_header)
            try:
                seller_prices, buyer_prices = get_platinum_costs()
                price_suggestion(seller_prices, buyer_prices)
            except TypeError as e:
                print(f"Price suggestion failed due to {e}")
            except Exception as e:
                print(e)
                break
            new_request = messagebox.askyesno("Confirm", "Would you like to search a new term?")
            print('*'*50)
    else:
        try:
            seller_prices, buyer_prices = get_platinum_costs()
            price_suggestion(seller_prices, buyer_prices)
        except TypeError as e:
            print(f"Price suggestion failed due to {e}")