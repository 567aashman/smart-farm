"""
SmartFarm AI - Market Service (Phase 16)
Fetches mandi/market prices for crops.

Now uses Tavily API and BeautifulSoup to scrape live data from the internet!
"""
import logging
import httpx
import os
import re
from bs4 import BeautifulSoup
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Reference wholesale prices (approximate, for display when API unavailable)
# Source: Ministry of Agriculture MSP data (updated periodically)
REFERENCE_MSP = {
    "wheat":     {"price": 2275, "unit": "quintal", "season": "2024-25", "type": "MSP"},
    "rice":      {"price": 2300, "unit": "quintal", "season": "2024-25", "type": "MSP"},
    "maize":     {"price": 2090, "unit": "quintal", "season": "2024-25", "type": "MSP"},
    "mustard":   {"price": 5950, "unit": "quintal", "season": "2024-25", "type": "MSP"},
    "potato":    {"price": None,  "unit": "quintal", "season": None,      "type": "variable"},
    "tomato":    {"price": None,  "unit": "quintal", "season": None,      "type": "variable"},
    "cotton":    {"price": 7121, "unit": "quintal", "season": "2024-25", "type": "MSP"},
    "sugarcane": {"price": 340,  "unit": "quintal", "season": "2024-25", "type": "SAP"},
    "chickpea":  {"price": 5440, "unit": "quintal", "season": "2024-25", "type": "MSP"},
    "soybean":   {"price": 4892, "unit": "quintal", "season": "2024-25", "type": "MSP"},
}

class MarketService:
    """
    Market/mandi price service.
    Uses Tavily API to find sources, BeautifulSoup to scrape content, 
    and Groq to extract the exact price. Falls back to MSP.
    """

    async def scrape_live_price(self, crop_name: str, location: str) -> Optional[float]:
        tavily_key = os.getenv("TAVILY_API_KEY")
        if not tavily_key:
            logger.warning("TAVILY_API_KEY not found. Skipping live scrape.")
            return None
            
        query = f"latest mandi market price of {crop_name} in {location} per quintal in rupees today"
        try:
            async with httpx.AsyncClient() as client:
                # 1. Get URL from Tavily Search API
                resp = await client.post(
                    "https://api.tavily.com/search",
                    json={
                        "api_key": tavily_key,
                        "query": query,
                        "search_depth": "basic",
                        "max_results": 1
                    },
                    timeout=3.0
                )
                if resp.status_code != 200:
                    return None
                    
                data = resp.json()
                results = data.get("results", [])
                if not results:
                    return None
                    
                url = results[0].get("url")
                if not url:
                    return None
                    
                # 2. Scrape the URL content using BeautifulSoup
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                page_resp = await client.get(url, headers=headers, timeout=3.0, follow_redirects=True)
                soup = BeautifulSoup(page_resp.text, 'html.parser')
                
                # Extract clean text from HTML
                text_content = soup.get_text(separator=' ', strip=True)
                
                # 3. Use Groq AI to precisely extract the numerical price from the scraped text
                from groq import Groq
                from backend.config import settings
                if settings.groq_api_key:
                    groq_client = Groq(api_key=settings.groq_api_key)
                    prompt = f"Extract the current price per quintal (in INR/Rs) for '{crop_name}' from this text. Return ONLY the numeric value (e.g., 2500). If you cannot find a price, return 'None'. Text snippet:\n{text_content[:3000]}"
                    
                    llm_resp = groq_client.chat.completions.create(
                        model="llama3-70b-8192",
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.0,
                        max_tokens=20
                    )
                    ans = llm_resp.choices[0].message.content.strip().replace(',', '')
                    match = re.search(r'\d+', ans)
                    if match:
                        return float(match.group())
                        
                return None
        except Exception as e:
            logger.error(f"Live scraping failed for {crop_name}: {e}")
            return None

    async def get_prices(self, crop_name: str, location: str) -> Dict[str, Any]:
        crop_key = crop_name.lower().strip()

        # ── 1. Attempt to Scrape Live Prices ──
        live_price = await self.scrape_live_price(crop_name, location)
        if live_price:
            return {
                "available": True,
                "crop_name": crop_name.title(),
                "market_name": location,
                "price_per_quintal": live_price,
                "unit": "quintal",
                "price_type": "Live Scraped",
                "date": datetime.utcnow().strftime("%Y-%m-%d"),
                "source": "Live Internet Scrape (Tavily + BS4)",
                "note": "This is a real-time price scraped from the internet using AI.",
            }

        # ── 2. Fallback to Reference MSP ──
        ref = REFERENCE_MSP.get(crop_key)
        if ref and ref["price"]:
            return {
                "available": True,
                "crop_name": crop_name.title(),
                "market_name": location,
                "price_per_quintal": ref["price"],
                "unit": ref["unit"],
                "price_type": ref["type"],
                "date": f"MSP {ref['season']}",
                "source": "Govt of India (MSP)",
                "note": (
                    f"Live data unavailable. This is the Minimum Support Price (MSP) for {ref['season']}. "
                ),
            }
        elif ref:
            return {
                "available": False,
                "crop_name": crop_name.title(),
                "market_name": location,
                "price_per_quintal": None,
                "note": "Live prices are highly variable. Scrape failed.",
                "source": "Live data not available",
            }
        else:
            return {
                "available": False,
                "crop_name": crop_name.title(),
                "market_name": location,
                "price_per_quintal": None,
                "note": f"Price data not available for {crop_name}.",
                "source": "Not available",
            }

    async def get_multiple_prices(self, crop_names: list, location: str) -> Dict:
        prices = []
        for crop in crop_names:
            price_data = await self.get_prices(crop, location)
            prices.append(price_data)

        return {
            "location": location,
            "prices": prices,
            "fetched_at": datetime.utcnow().isoformat(),
            "disclaimer": "Prices are either scraped live via Tavily/BS4 or provided as MSP reference.",
        }

# Module-level singleton
market_service = MarketService()
