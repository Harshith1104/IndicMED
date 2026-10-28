"""Bounded in-memory reuse, owned by the inference-locked application service."""
from collections import OrderedDict



class TranslationCache:
    def __init__(self, translator, limit=256):
        self.delegate, self.limit = translator, limit
        self.values = OrderedDict()

    def _translate(self, direction, text, language):
        key = direction, text, language
        if key not in self.values:
            # Never cache failures; repairing a checkpoint must allow retry.
            self.values[key] = getattr(self.delegate, direction)(text, language)
            if len(self.values) > self.limit:
                self.values.popitem(last=False)
        self.values.move_to_end(key)
        return self.values[key]

    def translate_to_english(self, text, language):
        return self._translate('translate_to_english', text, language)

    def translate_from_english(self, text, language):
        return self._translate('translate_from_english', text, language)


class EncoderCache:
    def __init__(self, encoder, limit=512):
        self.delegate, self.limit = encoder, limit
        self.values = OrderedDict()

    def encode(self, sentences, **kwargs):
        import numpy as np
        # The guard uses the same default encode call as semantic retrieval.
        # Other encoding options retain their original behavior.
        if kwargs or isinstance(sentences, str):
            return self.delegate.encode(sentences, **kwargs)
        missing = list(dict.fromkeys(text for text in sentences if text not in self.values))
        if missing:
            for text, vector in zip(missing, self.delegate.encode(missing)):
                self.values[text] = np.asarray(vector).copy()
        result = np.asarray([self.values[text] for text in sentences])
        for text in sentences:
            self.values.move_to_end(text)
        while len(self.values) > self.limit:
            self.values.popitem(last=False)
        return result
