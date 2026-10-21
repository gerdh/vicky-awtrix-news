import importlib.util
import json
import sys
import tempfile
import time
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import whoiswho_colors as colors
import whoiswho_surnames as surnames

PERSON = {'id': 'Q123', 'name': 'Ada Example', 'description': 'test researcher',
          'verified_human': True}
TEXT = 'Example presents a new research project today'


def listener():
    config = types.SimpleNamespace(AWTRIX_UID='test', MQTT_HOST='localhost')
    modules = {'config': config, 'paho': types.ModuleType('paho'),
               'paho.mqtt': types.ModuleType('paho.mqtt'),
               'paho.mqtt.client': types.ModuleType('paho.mqtt.client')}
    spec = importlib.util.spec_from_file_location('test_listener', Path(colors.__file__).with_name('whoiswho.py'))
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, modules):
        spec.loader.exec_module(module)
    return module


class ExplanationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.patch = patch.object(colors, 'CACHE_FILE', Path(self.tmp.name) / 'names.json')
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def test_surname_keeps_identity_and_span(self):
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        response.read.return_value = json.dumps({'choices': [{'message': {'content': json.dumps(
            {'people': [{'surface': 'Example', 'full_name': 'Ada Example'}]})}}]}).encode()
        with patch.object(surnames, 'urlopen', return_value=response), patch.object(surnames, 'lookup_person', return_value=PERSON):
            self.assertEqual(surnames.proposals(TEXT, 'en'), [(0, 7)])
            self.assertEqual(surnames.proposals(TEXT, 'en', with_people=True),
                             [{'span': (0, 7), 'person': PERSON}])

    def test_red_surname_is_explainable_without_second_ai_request(self):
        rows = [{'span': (0, 7), 'person': PERSON}]
        with patch.dict('os.environ', {'VICKY_WHOISWHO_SURNAMES': '1'}), patch.object(colors, 'resolve_people', return_value=rows):
            fragments = colors.fragments(TEXT, 'FFFFFF', 'en')
        self.assertEqual(''.join(p['t'] for p in fragments), TEXT)
        self.assertEqual(fragments[0]['c'], colors.RED)
        module = listener()
        with patch.object(colors, 'resolve_people', side_effect=AssertionError('must use cache')):
            self.assertEqual(module.verified_people(TEXT, 'en'), [PERSON])
        self.assertEqual(colors.cached_people(TEXT + ' changed', 'en'), [])
        self.assertEqual(colors.cached_people(TEXT, 'de'), [])

    def test_surname_failure_preserves_full_name(self):
        with patch.object(colors, 'extract_person_names', return_value=['Ada Example']), patch.object(colors, 'lookup_person', return_value=PERSON), patch.object(surnames, 'proposals', side_effect=OSError('offline')):
            rows = colors.resolve_people('Ada Example presents research', 'en', True)
            self.assertEqual(rows, [{'span': (0, 11), 'person': PERSON}])

    def test_legacy_spans_rebuilt(self):
        colors._save({colors._key(TEXT, 'en', False): {'ts': time.time(), 'spans': [[0, 7]]}})
        with patch.dict('os.environ', {'VICKY_WHOISWHO_SURNAMES': '0'}), patch.object(colors, 'resolve_people', return_value=[] ) as resolve:
            self.assertEqual(colors.fragments(TEXT, 'FFFFFF', 'en'), TEXT)
            resolve.assert_called_once()

    def test_expired_identity_not_used(self):
        colors._save({colors._key(TEXT, 'en', True): {'ts': time.time() - colors.TTL - 1, 'people': [PERSON]}})
        self.assertEqual(colors.cached_people(TEXT, 'en'), [])

    def test_button_cycles_and_wikipedia_failure_falls_back(self):
        module = listener()
        module.current_app = 'vicky_news_a_1'
        module.current_app_time = time.monotonic()
        module.headlines[module.current_app] = (TEXT, time.monotonic())
        second = dict(PERSON, id='Q456', name='Other Example')
        client = Mock()
        def immediate_thread(target, **kwargs):
            return types.SimpleNamespace(start=target)
        event = types.SimpleNamespace(topic='test/stats/buttonRight', payload=b'1')
        with patch.object(module, 'verified_people', return_value=[PERSON, second]), patch.object(module, 'language', return_value='en'), patch.object(module, 'wikipedia_intro', side_effect=OSError('offline')), patch.object(module.threading, 'Thread', side_effect=immediate_thread):
            module.handle(client, None, event)
            module.handle(client, None, event)
            messages = [json.loads(c.args[1]) for c in client.publish.call_args_list]
            self.assertEqual(messages[0]['text'], 'Ada Example: test researcher')
            self.assertEqual(messages[1]['text'], 'Other Example: test researcher')
            self.assertEqual(client.publish.call_args.args[0], 'test/notify')
            module.current_app_time -= 100
            module.handle(client, None, event)
            self.assertEqual(client.publish.call_count, 2)


if __name__ == '__main__':
    unittest.main()
