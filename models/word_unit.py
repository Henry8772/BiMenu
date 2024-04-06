class WordUnit:
    def __init__(self, word, confidence_score):
        self.word = word
        self.confidence_score = confidence_score

    def __str__(self):
        return self.word

    def __repr__(self):
        return self.word

    def to_dict(self):
        return {
            "word": self.word,
            "confidence_score": self.confidence_score
        }