from fastapi import FastAPI, HTTPException, Depends, Header, Request
from typing import Optional
import requests
import json
import os
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import uvicorn
import time
import threading

app = FastAPI(title="Multi-Purpose Data Scraping API", version="1.0.0")

CONFIG = {
    "API_KEY": "kingvon",
    "REQUEST_DELAY": 1,
    "MAX_REQUESTS_PER_MINUTE": 60
}

crypto_data_store = []
request_times = {}
data_lock = threading.Lock()

def rate_limit_check(request: Request):
    client_ip = request.client.host
    current_time = datetime.now()
    
    if client_ip not in request_times:
        request_times[client_ip] = []
    
    request_times[client_ip] = [
        req_time for req_time in request_times[client_ip] 
        if current_time - req_time < timedelta(minutes=1)
    ]
    
    if len(request_times[client_ip]) >= CONFIG["MAX_REQUESTS_PER_MINUTE"]:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    request_times[client_ip].append(current_time)
    return True

def verify_api_key(request: Request, x_api_key: str = Header(None)):
    rate_limit_check(request)
    if x_api_key != CONFIG["API_KEY"]:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return True

def load_data():
    with data_lock:
        return crypto_data_store.copy()

def save_data(data):
    with data_lock:
        crypto_data_store.extend(data)
        if len(crypto_data_store) > 1000:
            crypto_data_store[:] = crypto_data_store[-500:]

def scrape_crypto_prices(symbols=None, limit=10):
    time.sleep(CONFIG["REQUEST_DELAY"])
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc", 
        "per_page": limit,
        "page": 1
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    response = requests.get(url, params=params, headers=headers, timeout=10)
    response.raise_for_status()
    
    data = response.json()
    result = []
    
    symbol_list = symbols.split(",") if symbols else None
    
    for coin in data:
        if symbol_list and coin['symbol'].upper() not in [s.upper().strip() for s in symbol_list]:
            continue
            
        crypto_info = {
            "symbol": coin['symbol'].upper(),
            "name": coin['name'],
            "price": coin['current_price'],
            "market_cap": coin.get('market_cap'),
            "volume_24h": coin.get('total_volume'),
            "change_24h": coin.get('price_change_percentage_24h'),
            "timestamp": datetime.now().isoformat()
        }
        result.append(crypto_info)
    
    return result

def scrape_crypto_news(limit=5):
    url = "https://www.coindesk.com/arc/outboundfeeds/rss/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.content, 'xml')
    items = soup.find_all('item')[:limit]
    
    news_data = []
    for item in items:
        try:
            title = item.find('title').text.strip()
            link = item.find('link').text.strip()
            pub_date = item.find('pubDate').text.strip()
            description = item.find('description')
            desc_text = description.text.strip() if description else "No description"
            
            news_item = {
                "title": title,
                "url": link,
                "source": "CoinDesk",
                "published_at": pub_date,
                "summary": desc_text[:200] + "..." if len(desc_text) > 200 else desc_text
            }
            news_data.append(news_item)
        except:
            continue
    
    return news_data

def scrape_weather_data(city="Bangalore"):
    url = f"https://wttr.in/{city}?format=j1"
    headers = {
        "User-Agent": "curl/7.68.0"
    }
    
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    
    data = response.json()
    current = data['current_condition'][0]
    
    weather_info = {
        "city": city,
        "temperature": current['temp_C'] + "°C",
        "description": current['weatherDesc'][0]['value'],
        "humidity": current['humidity'] + "%",
        "wind_speed": current['windspeedKmph'] + " km/h",
        "timestamp": datetime.now().isoformat()
    }
    
    return weather_info

@app.get("/")
def root():
    return {"message": "Multi-Purpose Data Scraping API", "status": "running"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "timestamp": datetime.now()}

@app.get("/crypto/prices")
def get_crypto_prices(symbols: Optional[str] = None, authenticated: bool = Depends(verify_api_key)):
    try:
        result = scrape_crypto_prices(symbols, 10)
        
        existing_data = load_data()
        existing_data.extend(result)
        save_data(existing_data)
        
        return {"data": result, "count": len(result)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch crypto data: {str(e)}")

@app.get("/crypto/news")
def get_crypto_news(limit: int = 5, authenticated: bool = Depends(verify_api_key)):
    try:
        result = scrape_crypto_news(limit)
        return {"news": result, "count": len(result)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch news: {str(e)}")

@app.get("/weather")
def get_weather_data(city: str = "Bangalore", authenticated: bool = Depends(verify_api_key)):
    try:
        result = scrape_weather_data(city)
        return {"weather": result}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch weather: {str(e)}")

@app.get("/data/history")
def get_stored_data(limit: int = 50, authenticated: bool = Depends(verify_api_key)):
    try:
        data = load_data()
        if limit:
            data = data[-limit:]
        
        return {"stored_data": data, "total_records": len(data)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load data: {str(e)}")

@app.get("/data/stats")
def get_data_statistics(authenticated: bool = Depends(verify_api_key)):
    try:
        data = load_data()
        
        if not data:
            return {"message": "No data available"}
        
        symbols = {}
        total_records = len(data)
        
        for record in data:
            symbol = record.get('symbol', 'UNKNOWN')
            if symbol in symbols:
                symbols[symbol] += 1
            else:
                symbols[symbol] = 1
        
        stats = {
            "total_records": total_records,
            "unique_symbols": len(symbols),
            "symbol_counts": symbols,
            "last_updated": data[-1].get('timestamp') if data else None
        }
        
        return {"statistics": stats}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to calculate stats: {str(e)}")

@app.get("/config")
def get_config(request: Request, authenticated: bool = Depends(verify_api_key)):
    return {
        "config": {
            "max_requests_per_minute": CONFIG["MAX_REQUESTS_PER_MINUTE"],
            "request_delay": CONFIG["REQUEST_DELAY"],
            "storage": "in-memory",
            "current_records": len(crypto_data_store)
        }
    }

@app.delete("/data/clear")
def clear_stored_data(request: Request, authenticated: bool = Depends(verify_api_key)):
    try:
        with data_lock:
            crypto_data_store.clear()
        return {"message": "All stored data cleared successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear data: {str(e)}")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
