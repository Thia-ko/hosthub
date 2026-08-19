"""Unit tests for app.services.plans.get_features: the plan-default matrix and per-instance
override precedence. Pure function over plain attributes - no DB needed, same SimpleNamespace
convention as test_prompt_generator.py."""

from types import SimpleNamespace

from app.models.instance import Plan
from app.services.plans import get_features


def _instance(**overrides) -> SimpleNamespace:
    defaults = {
        "plan": Plan.STARTER,
        "ai_enabled_override": None,
        "campaigns_enabled_override": None,
        "api_access_enabled_override": None,
    }
    return SimpleNamespace(**{**defaults, **overrides})


def test_starter_plan_has_ai_but_not_campaigns_or_api_access():
    features = get_features(_instance(plan=Plan.STARTER))

    assert features.ai_enabled is True
    assert features.campaigns_enabled is False
    assert features.api_access_enabled is False


def test_pro_plan_adds_campaigns_but_not_api_access():
    features = get_features(_instance(plan=Plan.PRO))

    assert features.ai_enabled is True
    assert features.campaigns_enabled is True
    assert features.api_access_enabled is False


def test_enterprise_plan_has_everything():
    features = get_features(_instance(plan=Plan.ENTERPRISE))

    assert features.ai_enabled is True
    assert features.campaigns_enabled is True
    assert features.api_access_enabled is True


def test_override_true_grants_a_feature_the_plan_does_not_include():
    features = get_features(_instance(plan=Plan.STARTER, api_access_enabled_override=True))

    assert features.api_access_enabled is True


def test_override_false_revokes_a_feature_the_plan_includes():
    features = get_features(_instance(plan=Plan.ENTERPRISE, campaigns_enabled_override=False))

    assert features.campaigns_enabled is False


def test_override_none_inherits_the_plan_default():
    features = get_features(_instance(plan=Plan.PRO, campaigns_enabled_override=None))

    assert features.campaigns_enabled is True


def test_ai_enabled_can_be_overridden_off_on_any_plan():
    features = get_features(_instance(plan=Plan.ENTERPRISE, ai_enabled_override=False))

    assert features.ai_enabled is False
