from google.cloud import language
from google.cloud.language import types, enums

from nlp.thresholds import sentiment_score, sentiment_magnitude

from sinks.database import Database

from utils import fields

from datetime import datetime
import logging


class SentimentAnalyser(Database):

    def __init__(self):
        super().__init__()
        self._client = language.LanguageServiceClient()

    def analyse_titles(self, collection: str, documents: list) -> list:
        """Go through each document in a collection and analyse the sentiment."""
        sentences_analysis = []
        for doc in documents:
            id = doc.id
            doc_dict = doc.to_dict()
            if fields.SCORE_TIMESTAMP in doc_dict:
                continue
            document = types.Document(type=enums.Document.Type.PLAIN_TEXT, content=doc_dict.get("title"))
            annotations = self._client.analyze_sentiment(document=document)
            self.update_doc_from_firestore(
                collection,
                id,
                self.flag_negative_entities(annotations)
            )
            sentences_analysis.append(annotations.sentences)
        logging.info("performed sentiment analysis on %d documents" % (len(sentences_analysis)))
        return sentences_analysis

    def flag_negative_entities(self, annotations: dict) -> dict:
        negative_flag = False
        negative_count = 0
        parameters = {
            fields.SENTIMENT_SCORE: round(annotations.document_sentiment.score, 4),
            fields.SENTIMENT_MAGNITUDE: round(annotations.document_sentiment.magnitude, 4)
        }
        for sentence in annotations.sentences:
            if sentiment_score(sentence) and sentiment_magnitude(sentence):
                negative_flag = True
                negative_count += 1
        parameters[fields.NEGATIVE_FLAG] = negative_flag
        parameters[fields.NEGATIVE_SENTENCES_COUNT] = negative_count
        parameters[fields.SCORE_TIMESTAMP] = datetime.now().isoformat()
        return parameters
