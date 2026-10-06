"""
Tests para TwitterSentimentAnalyzer (specs/031-wyckoff-twitter-sentiment/).

Ninguna llamada de red real -- requests.get/post siempre mockeados.
"""
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

import pytest

from analysis.twitter_sentiment import (
    MIN_AUTHOR_FOLLOWERS,
    MIN_LIKE_COUNT,
    TwitterSentimentAnalyzer,
    TWITTER_DATE_FORMAT,
)


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


def _dated_tweet(text, minutes_ago, likes=5, followers=1_000, views=10):
    created = (datetime(2026, 9, 29, 12, 0, tzinfo=timezone.utc) - timedelta(minutes=minutes_ago))
    return {
        'text': text,
        'likeCount': likes,
        'viewCount': views,
        'createdAt': created.strftime(TWITTER_DATE_FORMAT),
        'author': {'userName': 'alguien', 'followers': followers},
    }


class TestSpamScreen:
    def test_zero_likes_and_small_accounts_are_left_out_of_velocity_and_gemini(self, monkeypatch):
        monkeypatch.setenv('GETXAPI_API_KEY', 'k1')
        monkeypatch.setenv('GEMINI_API_KEY', 'k2')
        analyzer = TwitterSentimentAnalyzer(enabled=True)
        # Dos tuits reales separados 60 min = 1 mencion/h. El spam junto inflaria la velocidad.
        real = [
            _dated_tweet('panic selling', minutes_ago=0, likes=4, followers=2_000),
            _dated_tweet('this is over', minutes_ago=60, likes=3, followers=500),
        ]
        spam = [
            _dated_tweet('airdrop claim now', minutes_ago=1, likes=0, followers=50_000, views=90_000),
            _dated_tweet('join my telegram', minutes_ago=2, likes=20, followers=MIN_AUTHOR_FOLLOWERS - 1),
        ]
        gemini_payload = {
            'sentiment_extreme': 'capitulation', 'social_spike_confirmed': False,
            'catalyst_present': False, 'summary': 'Capitulan.',
        }
        with patch('analysis.twitter_sentiment.requests.get',
                   return_value=_mock_response({'tweets': real + spam})) as mock_get, \
             patch('analysis.twitter_sentiment.requests.post',
                   return_value=_mock_response(_gemini_response(gemini_payload))) as mock_post:
            result = analyzer.analyze('SOL', 'hot')

        assert result['current'] == pytest.approx(1.0)
        assert result['max_views'] == 10
        assert 'airdrop' not in mock_post.call_args.kwargs['json']['contents'][0]['parts'][0]['text']
        assert 'join my telegram' not in mock_post.call_args.kwargs['json']['contents'][0]['parts'][0]['text']
        assert 'panic selling' in mock_post.call_args.kwargs['json']['contents'][0]['parts'][0]['text']
        assert mock_get.call_count == 2

    def test_a_page_of_only_spam_skips_gemini(self, monkeypatch):
        monkeypatch.setenv('GETXAPI_API_KEY', 'k1')
        monkeypatch.setenv('GEMINI_API_KEY', 'k2')
        analyzer = TwitterSentimentAnalyzer(enabled=True)
        spam = [_dated_tweet('airdrop', minutes_ago=i, likes=0, followers=10) for i in range(5)]
        with patch('analysis.twitter_sentiment.requests.get', return_value=_mock_response({'tweets': spam})), \
             patch('analysis.twitter_sentiment.requests.post') as mock_post:
            assert analyzer.analyze('SOL', 'hot') is None
        mock_post.assert_not_called()

    def test_missing_like_and_follower_fields_are_kept(self):
        kept = TwitterSentimentAnalyzer._screen_spam([
            {'text': 'sin campos', 'createdAt': 'Tue Sep 29 12:00:00 +0000 2026'},
            {'text': 'likes en texto', 'likeCount': '0', 'author': {'followers': '3'}},
            {'text': 'cero likes', 'likeCount': 0, 'author': {'followers': 5_000}},
            {'text': 'cuenta chica', 'likeCount': 8, 'author': {'followers': 12}},
            'no es un tuit',
        ])
        assert [t['text'] for t in kept] == ['sin campos', 'likes en texto']

    def test_one_like_and_exact_follower_floor_stay(self):
        tweet = _dated_tweet('ok', minutes_ago=0, likes=MIN_LIKE_COUNT, followers=MIN_AUTHOR_FOLLOWERS)
        assert TwitterSentimentAnalyzer._keep_tweet(tweet) is True


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

    def test_summary_is_html_escaped(self):
        section = TwitterSentimentAnalyzer.format_section({
            'current': None, 'baseline': None, 'ratio': None, 'max_views': 0,
            'sentiment_extreme': 'none', 'social_spike_confirmed': False,
            'catalyst_present': False, 'summary': 'ETFs & ballenas <b>rompen</b>',
        })
        assert '&amp;' in section
        assert '&lt;b&gt;' in section
        assert '<b>rompen</b>' not in section

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


# ─────────────────────────────────────────────────────────────────────────────
# QA adversarial: entradas mal formadas y tipos inesperados de un LLM/terceros.
# ─────────────────────────────────────────────────────────────────────────────

class TestMentionsPerHourAdversarial:
    def test_malformed_created_at_values_are_skipped(self):
        base = datetime(2026, 9, 29, 12, 0, tzinfo=timezone.utc)
        tweets = [
            {'createdAt': 'no es fecha'},
            {'createdAt': None},
            {},
            {'createdAt': 1234567890},
            {'createdAt': (base - timedelta(hours=1)).strftime(TWITTER_DATE_FORMAT)},
            {'createdAt': base.strftime(TWITTER_DATE_FORMAT)},
        ]
        assert TwitterSentimentAnalyzer._mentions_per_hour(tweets) == pytest.approx(1.0)

    def test_all_tweets_same_timestamp_returns_none(self):
        ts = datetime(2026, 9, 29, 12, 0, tzinfo=timezone.utc).strftime(TWITTER_DATE_FORMAT)
        tweets = [{'createdAt': ts} for _ in range(10)]
        assert TwitterSentimentAnalyzer._mentions_per_hour(tweets) is None

    def test_tweets_without_created_at_return_none(self):
        assert TwitterSentimentAnalyzer._mentions_per_hour([{'text': 'a'}, {'text': 'b'}]) is None

    def test_equivalent_instants_with_different_offsets_have_zero_span(self):
        tweets = [
            {'createdAt': 'Tue Sep 29 12:00:00 +0000 2026'},
            {'createdAt': 'Tue Sep 29 09:00:00 -0300 2026'},  # mismo instante UTC
        ]
        assert TwitterSentimentAnalyzer._mentions_per_hour(tweets) is None


class TestAnalyzeMalformedResponses:
    def _analyzer(self, monkeypatch):
        monkeypatch.setenv('GETXAPI_API_KEY', 'k1')
        monkeypatch.setenv('GEMINI_API_KEY', 'k2')
        return TwitterSentimentAnalyzer(enabled=True)

    def test_getxapi_json_response_is_a_list_returns_none(self, monkeypatch):
        analyzer = self._analyzer(monkeypatch)
        with patch('analysis.twitter_sentiment.requests.get',
                   return_value=_mock_response([{'text': 'x'}])):
            assert analyzer.analyze('SOL', 'hot') is None

    def test_getxapi_response_without_tweets_key_returns_none(self, monkeypatch):
        analyzer = self._analyzer(monkeypatch)
        with patch('analysis.twitter_sentiment.requests.get',
                   return_value=_mock_response({'other': 1})):
            assert analyzer.analyze('SOL', 'hot') is None

    def test_gemini_json_list_keeps_velocity_only(self, monkeypatch):
        analyzer = self._analyzer(monkeypatch)
        with patch('analysis.twitter_sentiment.requests.get',
                   return_value=_mock_response(_tweets_spanning(n=3, minutes_apart=5))), \
             patch('analysis.twitter_sentiment.requests.post',
                   return_value=_mock_response([1, 2, 3])):
            result = analyzer.analyze('SOL', 'hot')
        assert result is not None
        assert result['sentiment_extreme'] is None

    def test_gemini_wrong_typed_fields_do_not_break_formatting(self, monkeypatch):
        analyzer = self._analyzer(monkeypatch)
        payload = {'sentiment_extreme': ['capitulation'], 'social_spike_confirmed': 'yes',
                   'catalyst_present': 1, 'summary': 123}
        with patch('analysis.twitter_sentiment.requests.get',
                   return_value=_mock_response(_tweets_spanning(n=3, minutes_apart=5))), \
             patch('analysis.twitter_sentiment.requests.post',
                   return_value=_mock_response(_gemini_response(payload))):
            result = analyzer.analyze('SOL', 'hot')

        assert result['sentiment_extreme'] == ['capitulation']
        section = TwitterSentimentAnalyzer.format_section(result)
        assert isinstance(section, str)
        assert '123' in section


class TestFormatSectionAdversarial:
    def test_unhashable_sentiment_extreme_does_not_crash(self):
        section = TwitterSentimentAnalyzer.format_section(
            {'sentiment_extreme': ['capitulation'], 'summary': ''})
        assert section == ''

    def test_ratio_without_current_or_baseline_does_not_crash(self):
        section = TwitterSentimentAnalyzer.format_section(
            {'ratio': 2.0, 'current': None, 'baseline': None, 'summary': ''})
        assert isinstance(section, str)
        assert '2.0x' not in section

    def test_non_numeric_max_views_does_not_crash(self):
        section = TwitterSentimentAnalyzer.format_section({'max_views': 'muchas', 'summary': ''})
        assert isinstance(section, str)
        assert 'viral' not in section.lower()

    def test_zero_values_are_shown(self):
        section = TwitterSentimentAnalyzer.format_section(
            {'current': 0.0, 'baseline': 0.0, 'ratio': 0.0, 'summary': ''})
        assert '0.0/h' in section

    def test_negative_ratio_does_not_crash(self):
        section = TwitterSentimentAnalyzer.format_section(
            {'current': 1.0, 'baseline': 3.0, 'ratio': -0.5, 'summary': ''})
        assert '-0.5x' in section

    def test_summary_html_escape_is_complete(self):
        section = TwitterSentimentAnalyzer.format_section(
            {'summary': '<img src=x onerror=alert(1)>&amp; <b>negrita</b>'})
        assert '<img' not in section
        assert '&lt;img' in section
        assert '&amp;amp;' in section           # '&' literal escapado (no se interpreta)
        assert '&lt;b&gt;negrita&lt;/b&gt;' in section
