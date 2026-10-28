import io
import json
import unittest
from unittest.mock import patch
import whoiswho_extract as extractor


class ExtractTests(unittest.TestCase):
    def test_actual_ha41_response(self):
        reply = {'choices': [{'message': {'content': '{"names":["Emmanuel","Macron"]}'}}]}
        with patch.object(extractor, 'urlopen', return_value=io.BytesIO(json.dumps(reply).encode())):
            self.assertEqual(extractor.extract_person_names('Emmanuel Macron présente un nouveau projet'), ['Emmanuel Macron'])

    def test_separate_people_are_not_joined(self):
        names = ['Emmanuel', 'Macron', 'Donald', 'Trump']
        self.assertEqual(extractor.normalize_names(names, 'Emmanuel Macron rencontre Donald Trump'), ['Emmanuel Macron', 'Donald Trump'])

    def test_no_join_over_punctuation_or_missing_words(self):
        for headline in ['Emmanuel rencontre Macron', 'Emmanuel, Macron', 'Emmanuel-Macron']:
            self.assertEqual(extractor.normalize_names(['Emmanuel', 'Macron'], headline), [])

    def test_no_completion_of_surname(self):
        self.assertEqual(extractor.normalize_names(['Emmanuel', 'Macron'], 'Macron présente un projet'), [])

    def test_no_partial_word_match(self):
        self.assertEqual(extractor.normalize_names(['Emmanuel', 'Macron'], 'XEmmanuel Macronville'), [])

    def test_existing_full_names_and_duplicates(self):
        self.assertEqual(extractor.normalize_names(['Emmanuel Macron', 'Emmanuel', 'Macron', None, 12], 'Emmanuel Macron parle'), ['Emmanuel Macron'])

    def test_source_order_and_unicode(self):
        self.assertEqual(extractor.normalize_names(['Émile', 'Zola'], 'Émile Zola écrit'), ['Émile Zola'])
        self.assertEqual(extractor.normalize_names(['Macron', 'Emmanuel'], 'Emmanuel Macron parle'), ['Emmanuel Macron'])

    def test_invented_full_name_rejected(self):
        self.assertEqual(extractor.normalize_names(['Emmanuel Macron'], 'Un président parle'), [])

if __name__ == '__main__':
    unittest.main()
