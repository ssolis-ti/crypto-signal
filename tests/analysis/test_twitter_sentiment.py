"""
Tests para TwitterSentimentAnalyzer (specs/031-wyckoff-twitter-sentiment/).

Ninguna llamada de red real -- requests.get/post siempre mockeados.
"""
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

import pytest

from analysis.twitter_sentiment import TwitterSentimentAnalyzer, TWITTER_DATE_FORMAT


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

        assert result['sentiment_extreme'] == 'capitulation'
        assert result['social_spike_confirmed'] is True
        assert result['catalyst_present'] is False
        assert result['summary'] == 'La comunidad esta capitulando.'
        assert mock_get.call_count == 2  # ahora + hace 7 dias
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

    def test_gemini_invalid_json_keeps_velocity_only(self, monkeypatch):
        monkeypatch.setenv('GETXAPI_API_KEY', 'k1')
        monkeypatch.setenv('GEMINI_API_KEY', 'k2')
        analyzer = TwitterSentimentAnalyzer(enabled=True)

        tweets_payload = {'tweets': [{'text': 'hello'}]}
        garbage_gemini = {'candidates': [{'content': {'parts': [{'text': 'not json at all'}]}}]}

        with patch('analysis.twitter_sentiment.requests.get', return_value=_mock_response(tweets_payload)), \
             patch('analysis.twitter_sentiment.requests.post', return_value=_mock_response(garbage_gemini)):
            result = analyzer.analyze('SOL', 'hot')

        assert result is not None
        assert result['sentiment_extreme'] is None

    def test_gemini_network_error_keeps_velocity_only(self, monkeypatch):
        monkeypatch.setenv('GETXAPI_API_KEY', 'k1')
        monkeypatch.setenv('GEMINI_API_KEY', 'k2')
        analyzer = TwitterSentimentAnalyzer(enabled=True)

        with patch('analysis.twitter_sentiment.requests.get',
                    return_value=_mock_response({'tweets': [{'text': 'hi'}]})), \
             patch('analysis.twitter_sentiment.requests.post', side_effect=Exception("network down")):
            result = analyzer.analyze('SOL', 'hot')

        assert result is not None
        assert result['sentiment_extreme'] is None


def _tweets_spanning(n, minutes_apart, views=0):
    base = datetime(2026, 9, 29, 12, 0, tzinfo=timezone.utc)
    return {'tweets': [
        {'text': f't{i}', 'viewCount': views,
         'createdAt': (base - timedelta(minutes=i * minutes_apart)).strftime(TWITTER_DATE_FORMAT)}
        for i in range(n)
    ]}


class TestMentionVelocity:
    def test_mentions_per_hour_from_time_span(self):
        tweets = _tweets_spanning(n=13, minutes_apart=5)['tweets']  # 12 intervalos en 60 min
        assert TwitterSentimentAnalyzer._mentions_per_hour(tweets) == pytest.approx(12.0)

    def test_mentions_per_hour_needs_two_dated_tweets(self):
        assert TwitterSentimentAnalyzer._mentions_per_hour([{'text': 'x'}]) is None
        assert TwitterSentimentAnalyzer._mentions_per_hour([]) is None

    def test_ratio_compares_now_against_seven_days_ago(self, monkeypatch):
        monkeypatch.setenv('GETXAPI_API_KEY', 'k1')
        analyzer = TwitterSentimentAnalyzer(enabled=True)
        now_resp = _mock_response(_tweets_spanning(n=13, minutes_apart=5, views=80_000))   # 12/h
        past_resp = _mock_response(_tweets_spanning(n=13, minutes_apart=20))               # 3/h

        with patch('analysis.twitter_sentiment.requests.get', side_effect=[now_resp, past_resp]) as mock_get:
            velocity = analyzer.mention_velocity('SOL')

        assert velocity['current'] == pytest.approx(12.0)
        assert velocity['baseline'] == pytest.approx(3.0)
        assert velocity['ratio'] == pytest.approx(4.0)
        assert velocity['max_views'] == 80_000
        baseline_query = mock_get.call_args_list[1].kwargs['params']['q']
        assert baseline_query.startswith('$SOL until_time:')

    def test_format_shows_acceleration_and_viral(self):
        section = TwitterSentimentAnalyzer.format_section({
            'current': 12.0, 'baseline': 3.0, 'ratio': 4.0, 'max_views': 80_000,
            'sentiment_extreme': None, 'social_spike_confirmed': False,
            'catalyst_present': False, 'summary': '',
        })
        assert '4.0x' in section
        assert 'acelerando' in section
        assert 'Tweet viral' in section


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
