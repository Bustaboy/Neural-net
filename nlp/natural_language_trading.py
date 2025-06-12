# nlp/natural_language_trading.py
from transformers import pipeline
import spacy

class NaturalLanguageTrader:
    """Execute trades using natural language commands"""
    
    def __init__(self):
        self.nlp = spacy.load("en_core_web_trf")
        self.intent_classifier = pipeline("text-classification", 
                                        model="finbert-trading-intent")
        
    def parse_trade_command(self, command: str) -> Dict:
        """Parse natural language trading command"""
        # Example: "Buy 0.5 Bitcoin when it drops below 30k"
        
        doc = self.nlp(command)
        
        trade_params = {
            'action': None,
            'quantity': None,
            'symbol': None,
            'condition': None,
            'price': None
        }
        
        # Extract entities
        for ent in doc.ents:
            if ent.label_ == "MONEY":
                trade_params['price'] = self._parse_price(ent.text)
            elif ent.label_ == "QUANTITY":
                trade_params['quantity'] = float(ent.text)
                
        # Extract action
        for token in doc:
            if token.text.lower() in ['buy', 'sell', 'long', 'short']:
                trade_params['action'] = token.text.lower()
                
        return trade_params
