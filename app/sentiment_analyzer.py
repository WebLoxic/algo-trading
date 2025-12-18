# sentiment_analyzer.py
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from threading import Lock
_nltk_ready = False
_lock = Lock()

def _ensure_nltk():
    global _nltk_ready
    with _lock:
        if not _nltk_ready:
            try:
                nltk.data.find('sentiment/vader_lexicon.zip')
            except:
                nltk.download('vader_lexicon')
            _nltk_ready = True

class SentimentAnalyzer:
    def __init__(self):
        _ensure_nltk()
        self.sid = SentimentIntensityAnalyzer()

    def score(self, headline):
        s = self.sid.polarity_scores(headline)
        return s  # dict with compound, pos, neu, neg

sentiment = SentimentAnalyzer()
