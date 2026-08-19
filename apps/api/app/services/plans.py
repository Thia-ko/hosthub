from dataclasses import dataclass

from app.models.instance import Instance, Plan


@dataclass(frozen=True)
class InstanceFeatures:
    ai_enabled: bool
    campaigns_enabled: bool
    api_access_enabled: bool


# Default feature matrix per plan. STARTER covers the core product every client already has
# today (AI auto-reply + human handoff); PRO adds mass broadcast (campaigns); ENTERPRISE adds
# the external API (outbound webhooks + API keys, app.api.v1.routers.external/api_keys) for a
# client's own dev team or n8n. "Chatbot sem IA" (a non-AI, flow-based reply engine) isn't
# implemented yet, so it has no flag here - ai_enabled exists precisely so that gap can be
# closed later without another schema change.
PLAN_DEFAULTS: dict[Plan, InstanceFeatures] = {
    Plan.STARTER: InstanceFeatures(ai_enabled=True, campaigns_enabled=False, api_access_enabled=False),
    Plan.PRO: InstanceFeatures(ai_enabled=True, campaigns_enabled=True, api_access_enabled=False),
    Plan.ENTERPRISE: InstanceFeatures(ai_enabled=True, campaigns_enabled=True, api_access_enabled=True),
}


def get_features(instance: Instance) -> InstanceFeatures:
    """Effective feature set for an instance: the selected plan's defaults, with any explicit
    per-instance override (Instance.*_override, null = inherit) taking precedence - lets a
    custom deal (e.g. PRO pricing with API access for one client) skip inventing a one-off plan."""
    defaults = PLAN_DEFAULTS[instance.plan]
    return InstanceFeatures(
        ai_enabled=instance.ai_enabled_override if instance.ai_enabled_override is not None else defaults.ai_enabled,
        campaigns_enabled=(
            instance.campaigns_enabled_override
            if instance.campaigns_enabled_override is not None
            else defaults.campaigns_enabled
        ),
        api_access_enabled=(
            instance.api_access_enabled_override
            if instance.api_access_enabled_override is not None
            else defaults.api_access_enabled
        ),
    )
