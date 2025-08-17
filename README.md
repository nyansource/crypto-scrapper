# crypto-scraper-api

REST API for scraping cryptocurrency prices, financial news, and weather data made for the assignment :3

## Dependencies

```bash
pip install fastapi uvicorn requests beautifulsoup4 lxml
```

## Usage

```bash
python main.py
```

API runs on `http://localhost:8000`

## Endpoints

- `GET /crypto/prices` - cryptocurrency market data
- `GET /crypto/news` - financial news headlines  
- `GET /weather` - weather information
- `GET /data/history` - stored data
- `GET /data/stats` - analytics
- `GET /config` - configuration

## Authentication

Add header: `x-api-key: kingvon`

## Examples

```bash
# Get crypto prices
curl -H "x-api-key: kingvon" http://localhost:8000/crypto/prices

# Get specific cryptocurrencies
curl -H "x-api-key: kingvon" "http://localhost:8000/crypto/prices?symbols=btc,eth"

# Get news
curl -H "x-api-key: kingvon" http://localhost:8000/crypto/news

# Get weather
curl -H "x-api-key: kingvon" "http://localhost:8000/weather?city=Bangalore"
```

## Documentation

Interactive API documentation available at `http://localhost:8000/docs`

## License

MIT
