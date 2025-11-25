"""Gemini API client with Google Search grounding."""

import requests
import json
import os
from typing import Dict, Any, List, Optional
from config.settings import settings

class GeminiSearchClient:
    """Client for Gemini API with Google Search grounding."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize client.
        
        Args:
            api_key: Gemini API key (defaults to settings)
        """
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent"
        
    def search(self, query: str) -> str:
        """Perform a grounded search query.
        
        Args:
            query: The search query
            
        Returns:
            The generated text response with grounding
        """
        url = f"{self.base_url}?key={self.api_key}"
        
        payload = {
            "contents": [{
                "parts": [{"text": query}]
            }],
            "tools": [{
                "googleSearch": {}
            }]
        }
        
        try:
            response = requests.post(
                url, 
                headers={"Content-Type": "application/json"},
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            
            # Extract text from candidates
            if "candidates" in data and data["candidates"]:
                parts = data["candidates"][0]["content"]["parts"]
                text = "".join([part["text"] for part in parts if "text" in part])
                return text
                
            return "No information found."
            
        except Exception as e:
            print(f"Gemini search error: {e}")
            return f"Error searching for: {query}"

    def get_match_context(self, home_team: str, away_team: str) -> Dict[str, Any]:
        """Get comprehensive context for a match.
        
        Args:
            home_team: Home team name
            away_team: Away team name
            
        Returns:
            Dictionary with news, squads, and sentiment
        """
        context = {}
        
        # 1. News & Injuries
        news_query = f"Latest team news and injury report for {home_team} vs {away_team} match today. Key missing players?"
        context['news'] = self.search(news_query)
        
        # 2. Recent Form
        form_query = f"Recent form and last 5 match results for {home_team} and {away_team}. Who is in better form?"
        context['form'] = self.search(form_query)
        
        # 3. Sentiment/Prediction
        sentiment_query = f"What are the pundits and fans predicting for {home_team} vs {away_team}? Who is the favorite?"
        context['sentiment'] = self.search(sentiment_query)
        
        return context
