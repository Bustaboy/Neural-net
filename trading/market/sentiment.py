# market/sentiment.py
import requests
from transformers import pipeline

class SentimentAnalyzer:
    def __init__(self):
        self.classifier = pipeline("sentiment-analysis")

    def analyze_market_sentiment(self, news_articles: List[str]) -> float:
        scores = [self.classifier(article)[0]['score'] for article in news_articles]
        return sum(scores) / len(scores) if scores else 0.5
