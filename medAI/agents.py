import requests
from bs4 import BeautifulSoup
from googlesearch import search
import logging
from typing import List, Dict
import re

logger = logging.getLogger(__name__)

class MedicalSearchAgent:
    """Agent for searching medical information when local knowledge is insufficient"""
    
    def __init__(self):
        self.medical_sites = [
            "mayoclinic.org",
            "webmd.com", 
            "healthline.com",
            "who.int",
            "cdc.gov",
        ]
    
    def search_medical_info(self, query: str, max_results: int = 3) -> List[Dict]:
        """Search for medical information from trusted sources"""
        try:
            medical_query = f"{query} medical information health"
            results = []
            
            for site in self.medical_sites[:2]:
                site_query = f"{medical_query} site:{site}"
                try:
                    search_results = list(search(site_query, num=2, stop=2, pause=1))
                    for url in search_results:
                        content = self._extract_content(url)
                        if content:
                            results.append({
                                'url': url,
                                'content': content[:500],
                                'source': site
                            })
                            if len(results) >= max_results:
                                break
                except Exception as e:
                    logger.error(f"Search error for {site}: {e}")
                    continue
                
                if len(results) >= max_results:
                    break
            
            return results
            
        except Exception as e:
            logger.error(f"Medical search error: {e}")
            return []
    
    def _extract_content(self, url: str) -> str:
        """Extract relevant content from medical websites"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            for element in soup(['script', 'style', 'nav', 'footer', 'header']):
                element.decompose()
            
            content_selectors = [
                'article', 'main', '.content', '.article-body', 
                '.entry-content', '.post-content'
            ]
            
            content = ""
            for selector in content_selectors:
                elements = soup.select(selector)
                if elements:
                    content = elements[0].get_text(strip=True)
                    break
            
            if not content:
                content = soup.get_text(strip=True)

            content = re.sub(r'\s+', ' ', content)
            return content[:1000]
            
        except Exception as e:
            logger.error(f"Content extraction error for {url}: {e}")
            return ""

class ResponseEnhancementAgent:
    """Agent for enhancing and validating medical responses"""
    
    def __init__(self):
        self.search_agent = MedicalSearchAgent()
    
    def enhance_response(self, original_response: str, query: str, confidence_threshold: float = 0.7) -> Dict:
        """Enhance response with additional information if needed"""
        
        uncertainty_indicators = [
            "i don't know", "i'm not sure", "unclear", "uncertain",
            "cannot determine", "insufficient information", "not enough context"
        ]
        
        is_uncertain = any(indicator in original_response.lower() for indicator in uncertainty_indicators)
        is_short = len(original_response.split()) < 20
        
        if is_uncertain or is_short:
            logger.info(f"Response seems uncertain or short, searching for additional information")
            search_results = self.search_agent.search_medical_info(query)
            
            if search_results:
                enhanced_response = self._combine_responses(original_response, search_results)
                return {
                    'response': enhanced_response,
                    'enhanced': True,
                    'sources': [r['url'] for r in search_results]
                }
        
        return {
            'response': original_response,
            'enhanced': False,
            'sources': []
        }
    
    def _combine_responses(self, original: str, search_results: List[Dict]) -> str:
        """Combine original response with search results"""
        if not search_results:
            return original
        
        enhanced = original + "\n\nAdditional Information:\n"
        
        for i, result in enumerate(search_results[:2], 1):
            enhanced += f"\n{i}. From {result['source']}: {result['content'][:200]}...\n"
        
        enhanced += "\n⚠️ This information is supplemented from trusted medical sources. Always consult with healthcare professionals for personalized medical advice."
        
        return enhanced
