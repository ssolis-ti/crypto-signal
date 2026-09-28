"""
Tests para ConfigValidator.validate_required_config (specs/004-core-pipeline-test-coverage/).
"""
from notifications.validator import ConfigValidator


class TestValidateRequiredConfig:
    def test_all_required_values_present_returns_true(self):
        config = {'telegram': {'required': {'token': 'abc', 'chat_id': '123'}}}

        assert ConfigValidator.validate_required_config('telegram', config) is True

    def test_one_missing_required_value_returns_false(self):
        config = {'telegram': {'required': {'token': '', 'chat_id': '123'}}}

        assert ConfigValidator.validate_required_config('telegram', config) is False

    def test_no_required_key_returns_true(self):
        config = {'stdout': {}}

        assert ConfigValidator.validate_required_config('stdout', config) is True
