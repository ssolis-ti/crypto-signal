"""
Tests para TwitterSentimentAnalyzer (specs/031-wyckoff-twitter-sentiment/).

Ninguna llamada de red real -- requests.get/post siempre mockeados.
"""
import json
from unittest.mock import patch, MagicMock

import pytest

from analysis.twitter_sentiment import TwitterSentimentAnalyzer


def _mock_response(json_data, status_ok=True):
    resp = MagicMock()
    resp.json.return_value = json_data
    if status_ok:
        resp.raise_for_status.return_value = None
    else:
        resp.raise_for_status.side_effect = Exception("HTTP error")
    return resp


def _gemini_response(payload: dict):
    return {
        'candidates': [
            {'content': {'parts': [{'text': json.dumps(payload)}]}}
        ]
    }


class TestDisabledAndMissingCredentials:
    def test_disabled_returns_none_without_any_request(self):
        analyzer = TwitterSentimentAnalyzer(enabled=False)
        with patch('analysis.twitter_sentiment.requests.get') as mock_get:
            result = analyzer.analyze('SOL', 'hot')
        assert result is None
        mock_get.assert_not_called()

    def test_enabled_without_keys_returns_none(self, monkeypatch):
        monkeypatch.delenv('GETXAPI_API_KEY', raising=False)
        monkeypatch.delenv('GEMINI_API_KEY', raising=False)
        analyzer = TwitterSentimentAnalyzer(enabled=True)
        with patch('analysis.twitter_sentiment.requests.get') as mock_get:
            result = analyzer.analyze('SOL', 'hot')
        assert result is None
        mock_get.assert_not_called()


class TestHappyPath:
    def test_full_classification_flow(self, monkeypatch):
        monkeypatch.setenv('GETXAPI_API_KEY', 'test-getxapi-key')
        monkeypatch.setenv('GEMINI_API_KEY', 'test-gemini-key')
        analyzer = TwitterSentimentAnalyzer(enabled=True)

        tweets_payload = {'tweets': [{'text': 'panic selling everything'}, {'text': 'this is over'}]}
        gemini_payload = {
            'sentiment_extreme': 'capitulation',
            'social_spike_confirmed': True,
            'catalyst_present': False,
            'summary': 'La comunidad esta capitulando.',
        }

        with patch('analysis.twitter_sentiment.requests.get',
                    return_value=_mock_response(tweets_payload)) as mock_get, \
             patch('analysis.twitter_sentiment.requests.post',
                    return_value=_mock_response(_gemini_response(gemini_payload))) as mock_post:
            result = analyzer.analyze('SOL', 'hot')

        assert result == {
            'sentiment_extreme': 'capitulation',
            'social_spike_confirmed': True,
            'catalyst_present': False,
            'summary': 'La comunidad esta capitulando.',
        }
        mock_get.assert_called_once()
        mock_post.assert_called_once()

    def test_gemini_response_wrapped_in_markdown_fence_is_parsed(self, monkeypatch):
        monkeypatch.setenv('GETXAPI_API_KEY', 'k1')
        monkeypatch.setenv('GEMINI_API_KEY', 'k2')
        analyzer = TwitterSentimentAnalyzer(enabled=True)

        tweets_payload = {'tweets': [{'text': 'to the moon'}]}
        fenced_text = "```json\n" + json.dumps({
            'sentiment_extreme': 'euphoria', 'social_spike_confirmed': False,
            'catalyst_present': False, 'summary': 'Euforia generalizada.'
        }) + "\n```"
        gemini_raw = {'candidates': [{'content': {'parts': [{'text': fenced_text}]}}]}

        with patch('analysis.twitter_sentiment.requests.get', return_value=_mock_response(tweets_payload)), \
             patch('analysis.twitter_sentiment.requests.post', return_value=_mock_response(gemini_raw)):
            result = analyzer.analyze('DOGE', 'cold')

        assert result['sentiment_extreme'] == 'euphoria'


class TestDegradesSafe:
    def test_no_tweets_returns_none(self, monkeypatch):
        monkeypatch.setenv('GETXAPI_API_KEY', 'k1')
        monkeypatch.setenv('GEMINI_API_KEY', 'k2')
        analyzer = TwitterSentimentAnalyzer(enabled=True)

        with patch('analysis.twitter_sentiment.requests.get',
                    return_value=_mock_response({'tweets': []})) as mock_get, \
             patch('analysis.twitter_sentiment.requests.post') as mock_post:
            result = analyzer.analyze('SOL', 'hot')

        assert result is None
        mock_post.assert_not_called()

    def test_getxapi_network_error_is_caught(self, monkeypatch):
        monkeypatch.setenv('GETXAPI_API_KEY', 'k1')
        monkeypatch.setenv('GEMINI_API_KEY', 'k2')
        analyzer = TwitterSentimentAnalyzer(enabled=True)

        with patch('analysis.twitter_sentiment.requests.get', side_effect=Exception("timeout")):
            result = analyzer.analyze('SOL', 'hot')

        assert result is None

    def test_gemini_invalid_json_returns_none(self, monkeypatch):
        monkeypatch.setenv('GETXAPI_API_KEY', 'k1')
        monkeypatch.setenv('GEMINI_API_KEY', 'k2')
        analyzer = TwitterSentimentAnalyzer(enabled=True)

        tweets_payload = {'tweets': [{'text': 'hello'}]}
        garbage_gemini = {'candidates': [{'content': {'parts': [{'text': 'not json at all'}]}}]}

        with patch('analysis.twitter_sentiment.requests.get', return_value=_mock_response(tweets_payload)), \
             patch('analysis.twitter_sentiment.requests.post', return_value=_mock_response(garbage_gemini)):
            result = analyzer.analyze('SOL', 'hot')

        assert result is None

    def test_gemini_network_error_is_caught(self, monkeypatch):
        monkeypatch.setenv('GETXAPI_API_KEY', 'k1')
        monkeypatch.setenv('GEMINI_API_KEY', 'k2')
        analyzer = TwitterSentimentAnalyzer(enabled=True)

        with patch('analysis.twitter_sentiment.requests.get',
                    return_value=_mock_response({'tweets': [{'text': 'hi'}]})), \
             patch('analysis.twitter_sentiment.requests.post', side_effect=Exception("network down")):
            result = analyzer.analyze('SOL', 'hot')

        assert result is None


class TestFormatSection:
    def test_none_result_formats_to_empty_string(self):
        assert TwitterSentimentAnalyzer.format_section(None) == ''

    def test_full_result_includes_all_lines(self):
        result = {
            'sentiment_extreme': 'capitulation',
            'social_spike_confirmed': True,
            'catalyst_present': True,
            'summary': 'Resumen de prueba.',
        }
        section = TwitterSentimentAnalyzer.format_section(result)
        assert 'Capitulación' in section
        assert 'Pico de actividad social' in section
        assert 'catalizador' in section
        assert 'Resumen de prueba.' in section

    def test_minimal_result_omits_optional_lines(self):
        result = {
            'sentiment_extreme': 'none',
            'social_spike_confirmed': False,
            'catalyst_present': False,
            'summary': '',
        }
        section = TwitterSentimentAnalyzer.format_section(result)
        assert 'Sin señal clara' in section
        assert 'Pico de actividad social' not in section
        assert 'catalizador' not in section
