"""Firewall-related models for network device configurations.

This module contains Django models that define firewall configurations
and related network security components.
"""

import ipaddress
import re

from django.core.exceptions import ValidationError
from django.db import models
from nautobot.core.models.generics import BaseModel, ChangeLoggedModel, PrimaryModel

from ..choices.firewalls import (
    FAMILY_MATCH_CONDITIONS,
    JuniperFirewallFamilyChoices,
    JuniperFirewallFilterActionTypeChoices,
    JuniperFirewallMatchConditionTypeChoices,
    JuniperFirewallPolicerActionTypeChoices,
    JuniperPolicerBandwidthUnitChoices,
    JuniperPolicerBurstUnitChoices,
)
from .policies import JuniperPolicyPrefixList


class DisplayCacheMixin:
    """
    Mixin to provide efficient caching of get_FOO_display() method results.

    This mixin improves performance by caching the results of Django's
    get_FOO_display() methods, which can be expensive when called repeatedly
    in list views, admin interfaces, or API serializations.
    """

    def _get_cached_display(self, field_name: str, display_method_name: str) -> str:
        """
        Get cached display value for a choice field.

        :param field_name: Name of the model field
        :type field_name: str
        :param display_method_name: Name of the get_FOO_display method
        :type display_method_name: str
        :return: The display value for the choice field
        :rtype: str
        """
        cache_attr = f"_{field_name}_display_cache"

        if not hasattr(self, cache_attr) or getattr(self, cache_attr) is None:
            display_method = getattr(self, display_method_name)
            setattr(self, cache_attr, display_method())

        return getattr(self, cache_attr)

    def _clear_display_cache(self, *field_names: str) -> None:
        """
        Clear cached display values for specified fields.

        :param field_names: Names of fields whose caches should be cleared
        :type field_names: str
        """
        for field_name in field_names:
            cache_attr = f"_{field_name}_display_cache"
            if hasattr(self, cache_attr):
                setattr(self, cache_attr, None)


class JuniperFirewallFilter(DisplayCacheMixin, PrimaryModel):
    """
    Represents a Juniper firewall filter configuration.

    This model defines firewall filters used in Juniper devices for traffic
    filtering and security policies. Each filter can be applied to different
    protocol families (IPv4, IPv6, VPLS, etc.).
    """

    name = models.CharField(max_length=255, unique=True, help_text="Name of the firewall filter")

    description = models.CharField(
        max_length=255, blank=True, help_text="Optional description of the firewall filter purpose"
    )

    family = models.CharField(
        max_length=10, choices=JuniperFirewallFamilyChoices.choices, help_text="Protocol family this filter applies to"
    )

    class Meta:
        """Meta class for JuniperFirewallFilter model."""

        ordering = ["name"]
        verbose_name = "Juniper Firewall Filter"
        verbose_name_plural = "Juniper Firewall Filters"

    def __str__(self):
        """Return string representation of the firewall filter."""
        return f"{self.name} ({self.get_family_display()})"

    @property
    def family_display(self):
        """Return cached family display value."""
        return self._get_cached_display("family", "get_family_display")

    def save(self, *args, **kwargs):
        """Save the model and clear cached display values."""
        # Clear cached display values when family changes
        old_family = None
        if self.pk:
            try:
                old_instance = self.__class__.objects.get(pk=self.pk)
                old_family = old_instance.family
            except self.__class__.DoesNotExist:
                pass

        result = super().save(*args, **kwargs)

        # Clear cache if family changed
        if old_family is not None and old_family != self.family:
            self._clear_display_cache("family")

        return result

    def clean(self):
        """Validate the firewall filter configuration."""
        super().clean()

        if self.name:
            # Ensure name follows Juniper naming conventions (alphanumeric, hyphens, underscores)
            if not re.match(r"^[a-zA-Z0-9_-]+$", self.name):
                raise ValidationError(
                    {
                        "name": "Firewall filter name must contain only alphanumeric characters, hyphens, and underscores."
                    }
                )


class JuniperFirewallTerm(PrimaryModel):
    """
    Represents a term within a Juniper firewall filter.

    This model defines individual terms (rules) within firewall filters.
    Each term can match specific traffic conditions and apply actions.
    Terms are processed in order within their parent filter.
    """

    name = models.CharField(max_length=255, help_text="Name of the firewall term")

    description = models.CharField(
        max_length=255, blank=True, help_text="Optional description of the firewall term purpose"
    )

    order = models.IntegerField(default=0, help_text="Order in which this term is processed within the filter")

    enabled = models.BooleanField(default=True, help_text="Whether this firewall term is active")

    filter = models.ForeignKey(
        JuniperFirewallFilter,
        on_delete=models.CASCADE,
        related_name="terms",
        help_text="The firewall filter this term belongs to",
    )

    class Meta:
        """Meta class for JuniperFirewallTerm model."""

        ordering = ["filter", "order", "name"]
        verbose_name = "Juniper Firewall Term"
        verbose_name_plural = "Juniper Firewall Terms"
        unique_together = ["filter", "name"]

    def __str__(self):
        """Return string representation of the firewall term."""
        return f"{self.filter.name}::{self.name} (order: {self.order})"

    def clean(self):
        """Validate the firewall term configuration."""
        super().clean()

        if self.name:
            # Ensure name follows Juniper naming conventions (alphanumeric, hyphens, underscores)
            if not re.match(r"^[a-zA-Z0-9_-]+$", self.name):
                raise ValidationError(
                    {"name": "Firewall term name must contain only alphanumeric characters, hyphens, and underscores."}
                )


class JuniperFirewallFilterMatchCondition(DisplayCacheMixin, PrimaryModel):
    """Represents a match condition within a Juniper firewall term.

    This model defines specific match conditions that determine which traffic
    a firewall term applies to. Multiple conditions can be associated with
    a single term, and they are processed in order.
    """

    condition_type = models.CharField(
        max_length=100,
        choices=JuniperFirewallMatchConditionTypeChoices.choices,
        help_text="Type of match condition to apply",
    )

    value = models.CharField(
        max_length=255, help_text="Value for the match condition (may be serialized array for certain types)"
    )

    negate = models.BooleanField(default=False, help_text="Whether to negate this match condition")

    term = models.ForeignKey(
        JuniperFirewallTerm,
        on_delete=models.CASCADE,
        related_name="match_conditions",
        help_text="The firewall term this match condition belongs to",
    )

    order = models.IntegerField(default=0, help_text="Order in which this condition is processed within the term")

    class Meta:
        """Meta class for JuniperFirewallFilterMatchCondition model."""

        ordering = ["term", "order", "condition_type"]
        verbose_name = "Juniper Firewall Match Condition"
        verbose_name_plural = "Juniper Firewall Match Conditions"

    def __str__(self):
        """Return string representation of the match condition."""
        negate_prefix = "NOT " if self.negate else ""
        return f"{self.term.filter.name}::{self.term.name} - {negate_prefix}{self.condition_type_display}: {self.value}"

    @property
    def condition_type_display(self):
        """Return cached condition type display value."""
        return self._get_cached_display("condition_type", "get_condition_type_display")

    def save(self, *args, **kwargs):
        """Save the model and clear cached display values."""
        # Clear cached display values when condition_type changes
        old_condition_type = None
        if self.pk:
            try:
                old_instance = self.__class__.objects.get(pk=self.pk)
                old_condition_type = old_instance.condition_type
            except self.__class__.DoesNotExist:
                pass

        result = super().save(*args, **kwargs)

        # Clear cache if condition_type changed
        if old_condition_type is not None and old_condition_type != self.condition_type:
            self._clear_display_cache("condition_type")

        return result

    def clean(self):
        """Validate the match condition configuration."""
        super().clean()

        # Validate that condition type is valid for the filter family
        if self.term and self.term.filter and self.condition_type:
            self._validate_condition_family_compatibility()

        # Validate value format based on condition type
        if self.condition_type and self.value:
            self._validate_condition_value()

    def _validate_condition_family_compatibility(self):
        """Validate that the condition type is compatible with the filter family."""
        filter_family = JuniperFirewallFamilyChoices(self.term.filter.family)
        condition_type = JuniperFirewallMatchConditionTypeChoices(self.condition_type)

        valid_conditions = FAMILY_MATCH_CONDITIONS.get(filter_family, [])

        if condition_type not in valid_conditions:
            family_display = self.term.filter.family_display
            condition_display = self.condition_type_display
            raise ValidationError(
                {
                    "condition_type": f"Match condition '{condition_display}' "
                    f"is not valid for family '{family_display}'. "
                    f"See Juniper documentation for valid conditions per family."
                }
            )

    def _validate_condition_value(self):
        """Validate value format based on condition type."""
        if self.is_array_type:
            self._validate_array_value()
        else:
            self._validate_string_value()

    def _validate_array_value(self):
        """Validate array-type values."""
        if not self.value.strip():
            raise ValidationError({"value": "Array-type conditions require at least one value."})

        # For protocol, validate known protocols
        if self.condition_type in [
            JuniperFirewallMatchConditionTypeChoices.PROTOCOL,
            JuniperFirewallMatchConditionTypeChoices.PROTOCOL_EXCEPT,
        ]:
            self._validate_protocol_values()

    def _validate_protocol_values(self):
        """Validate protocol values for protocol-type conditions."""
        valid_protocols = {
            "tcp",
            "udp",
            "icmp",
            "igmp",
            "pim",
            "ospf",
            "bgp",
            "rip",
            "gre",
            "esp",
            "ah",
            "sctp",
            "ipv6",
            "ipv6-icmp",
            "ipv6-route",
            "ipv6-frag",
        }
        protocols = [p.strip().lower() for p in self.value.split(",")]
        invalid_protocols = [p for p in protocols if p not in valid_protocols]
        if invalid_protocols:
            raise ValidationError(
                {
                    "value": f"Invalid protocols: {', '.join(invalid_protocols)}. "
                    f"Valid protocols include: {', '.join(sorted(valid_protocols))}"
                }
            )

    def _validate_string_value(self):
        """Validate string-type values."""
        if not self.value.strip():
            raise ValidationError({"value": "String-type conditions require a value."})

        # For address types, validate format
        if self.condition_type in [
            JuniperFirewallMatchConditionTypeChoices.SOURCE_ADDRESS,
            JuniperFirewallMatchConditionTypeChoices.DESTINATION_ADDRESS,
            JuniperFirewallMatchConditionTypeChoices.ADDRESS,
            JuniperFirewallMatchConditionTypeChoices.IP_SOURCE_ADDRESS,
            JuniperFirewallMatchConditionTypeChoices.IP_DESTINATION_ADDRESS,
            JuniperFirewallMatchConditionTypeChoices.IPV6_SOURCE_ADDRESS,
            JuniperFirewallMatchConditionTypeChoices.IPV6_DESTINATION_ADDRESS,
        ]:
            self._validate_address_value()

        # For port types, validate port ranges
        if self.condition_type in [
            JuniperFirewallMatchConditionTypeChoices.SOURCE_PORT,
            JuniperFirewallMatchConditionTypeChoices.DESTINATION_PORT,
            JuniperFirewallMatchConditionTypeChoices.PORT,
        ]:
            self._validate_port_value()

    def _validate_address_value(self):
        """Validate IP address or subnet values."""
        value = self.value.strip()
        try:
            # Try to parse as IP network (includes single IPs and subnets)
            ipaddress.ip_network(value, strict=False)
        except ValueError:
            # If not a valid IP, check if it's a hostname or FQDN pattern
            if not re.match(r"^[a-zA-Z0-9.-]+$", value):
                raise ValidationError({"value": "Address must be a valid IP address, subnet, or hostname."})

    def _validate_port_value(self):
        """Validate port or port range values."""
        value = self.value.strip()

        # Check for port ranges (e.g., "80-443" or "1024-65535")
        if "-" in value:
            try:
                start_port, end_port = value.split("-", 1)
                start_port = int(start_port.strip())
                end_port = int(end_port.strip())

                if not (1 <= start_port <= 65535) or not (1 <= end_port <= 65535):
                    raise ValidationError({"value": "Port numbers must be between 1 and 65535."})

                if start_port >= end_port:
                    raise ValidationError({"value": "Start port must be less than end port in range."})

            except ValueError:
                raise ValidationError({"value": "Port range must be in format 'start-end' (e.g., '80-443')."})
        else:
            # Single port
            try:
                port = int(value)
                if not (1 <= port <= 65535):
                    raise ValidationError({"value": "Port number must be between 1 and 65535."})
            except ValueError:
                raise ValidationError({"value": "Port must be a number or range (e.g., '80' or '80-443')."})

    @property
    def is_array_type(self):
        """Check if this condition type expects array values."""
        array_condition_types = {
            JuniperFirewallMatchConditionTypeChoices.SOURCE_PREFIX_LIST,
            JuniperFirewallMatchConditionTypeChoices.DESTINATION_PREFIX_LIST,
            JuniperFirewallMatchConditionTypeChoices.PREFIX_LIST,
            JuniperFirewallMatchConditionTypeChoices.PROTOCOL,
            JuniperFirewallMatchConditionTypeChoices.PROTOCOL_EXCEPT,
            JuniperFirewallMatchConditionTypeChoices.DESTINATION_PORT_LIST,
            JuniperFirewallMatchConditionTypeChoices.SOURCE_PORT_LIST,
        }
        return self.condition_type in array_condition_types

    def get_value_as_list(self):
        """Return value as a list for array-type conditions."""
        if self.is_array_type and self.value:
            return [item.strip() for item in self.value.split(",") if item.strip()]
        return [self.value] if self.value else []

    @classmethod
    def get_valid_conditions_for_family(cls, family):
        """Get all valid match condition types for a given family.

        :param family: JuniperFirewallFamilyChoices enum value or string
        :type family: JuniperFirewallFamilyChoices | str
        :return: List of valid condition type choices
        :rtype: list[JuniperFirewallMatchConditionTypeChoices]
        """
        if isinstance(family, str):
            family = JuniperFirewallFamilyChoices(family)
        return FAMILY_MATCH_CONDITIONS.get(family, [])


class JuniperFirewallMatchConditionToPrefixList(BaseModel, ChangeLoggedModel):
    """
    Junction table for many-to-many relationship between match conditions and prefix lists.

    This model represents the association between firewall match conditions
    and policy prefix lists. A match condition can reference multiple prefix
    lists, and a prefix list can be used by multiple match conditions.
    """

    match_condition = models.ForeignKey(
        JuniperFirewallFilterMatchCondition,
        on_delete=models.CASCADE,
        related_name="prefix_list_associations",
        help_text="The match condition that references the prefix list",
    )

    prefix_list = models.ForeignKey(
        JuniperPolicyPrefixList,
        on_delete=models.CASCADE,
        related_name="match_condition_associations",
        help_text="The prefix list being referenced by the match condition",
    )

    class Meta:
        """Meta class for JuniperFirewallMatchConditionToPrefixList model."""

        ordering = ["match_condition", "prefix_list"]
        verbose_name = "Match Condition Prefix List Association"
        verbose_name_plural = "Match Condition Prefix List Associations"
        unique_together = ["match_condition", "prefix_list"]

    def __str__(self):
        """Return string representation of the association."""
        return f"{self.match_condition.term.filter.name}::{self.match_condition.term.name} -> {self.prefix_list.name}"

    def clean(self):
        """Validate the association configuration."""
        super().clean()

        # Validate that the match condition is a prefix list type
        if self.match_condition and self.match_condition.condition_type not in [
            JuniperFirewallMatchConditionTypeChoices.SOURCE_PREFIX_LIST,
            JuniperFirewallMatchConditionTypeChoices.DESTINATION_PREFIX_LIST,
        ]:
            raise ValidationError(
                {
                    "match_condition": "Match condition must be a prefix list type (source-prefix-list or destination-prefix-list)."
                }
            )


class JuniperFirewallPolicer(DisplayCacheMixin, PrimaryModel):
    """
    Represents a Juniper firewall policer configuration.

    This model defines policers used in Juniper devices for rate limiting
    and traffic shaping. Policers can be applied to firewall terms or
    actions to control bandwidth usage and burst rates.
    """

    name = models.CharField(max_length=255, unique=True, help_text="Name of the firewall policer")

    bandwidth_limit = models.IntegerField(
        null=True, blank=True, help_text="Bandwidth limit value (use with bandwidth_unit)"
    )

    bandwidth_unit = models.CharField(
        max_length=10,
        choices=JuniperPolicerBandwidthUnitChoices.choices,
        default=JuniperPolicerBandwidthUnitChoices.MBPS,
        help_text="Unit for bandwidth limit",
    )

    burst_limit = models.IntegerField(null=True, blank=True, help_text="Burst limit value (use with burst_unit)")

    burst_unit = models.CharField(
        max_length=10,
        choices=JuniperPolicerBurstUnitChoices.choices,
        default=JuniperPolicerBurstUnitChoices.BYTES,
        help_text="Unit for burst limit",
    )

    logical_interface_policer = models.BooleanField(
        default=False, help_text="Whether this is a logical interface policer"
    )

    description = models.CharField(max_length=255, blank=True, help_text="Optional description of the policer purpose")

    class Meta:
        """Meta class for JuniperFirewallPolicer model."""

        ordering = ["name"]
        verbose_name = "Juniper Firewall Policer"
        verbose_name_plural = "Juniper Firewall Policers"

    def __str__(self):
        """Return string representation of the firewall policer."""
        bandwidth_str = f"{self.bandwidth_limit}{self.bandwidth_unit}" if self.bandwidth_limit else "unlimited"
        return f"{self.name} ({bandwidth_str})"

    def clean(self):
        """Validate the firewall policer configuration."""
        super().clean()

        if self.name:
            # Ensure name follows Juniper naming conventions (alphanumeric, hyphens, underscores)
            if not re.match(r"^[a-zA-Z0-9_-]+$", self.name):
                raise ValidationError(
                    {"name": "Policer name must contain only alphanumeric characters, hyphens, and underscores."}
                )

        # Validate bandwidth configuration
        if self.bandwidth_limit is not None and self.bandwidth_limit <= 0:
            raise ValidationError({"bandwidth_limit": "Bandwidth limit must be a positive integer."})

        # Validate burst configuration
        if self.burst_limit is not None and self.burst_limit <= 0:
            raise ValidationError({"burst_limit": "Burst limit must be a positive integer."})

        # Warn if bandwidth is specified without a limit (though this might be valid in some cases)
        if self.bandwidth_limit is None and self.burst_limit is not None:
            # This could be a warning, but not necessarily an error
            pass

    @property
    def bandwidth_display(self):
        """Return formatted bandwidth limit display."""
        if self.bandwidth_limit is None:
            return "Unlimited"
        return f"{self.bandwidth_limit} {self.bandwidth_unit_display}"

    @property
    def bandwidth_unit_display(self):
        """Return cached bandwidth unit display value."""
        return self._get_cached_display("bandwidth_unit", "get_bandwidth_unit_display")

    @property
    def burst_display(self):
        """Return formatted burst limit display."""
        if self.burst_limit is None:
            return "Not specified"
        return f"{self.burst_limit} {self.burst_unit_display}"

    @property
    def burst_unit_display(self):
        """Return cached burst unit display value."""
        return self._get_cached_display("burst_unit", "get_burst_unit_display")

    def save(self, *args, **kwargs):
        """Save the model and clear cached display values."""
        # Clear cached display values when units change
        old_bandwidth_unit = None
        old_burst_unit = None
        if self.pk:
            try:
                old_instance = self.__class__.objects.get(pk=self.pk)
                old_bandwidth_unit = old_instance.bandwidth_unit
                old_burst_unit = old_instance.burst_unit
            except self.__class__.DoesNotExist:
                pass

        result = super().save(*args, **kwargs)

        # Clear cache if units changed
        if (old_bandwidth_unit is not None and old_bandwidth_unit != self.bandwidth_unit) or (
            old_burst_unit is not None and old_burst_unit != self.burst_unit
        ):
            self._clear_display_cache("bandwidth_unit", "burst_unit")

        return result

    @property
    def is_rate_limited(self):
        """Return whether this policer has any rate limiting configured."""
        return self.bandwidth_limit is not None or self.burst_limit is not None

    def get_policer_config_summary(self):
        """Return a summary of the policer configuration."""
        config_parts = []

        if self.bandwidth_limit:
            config_parts.append(f"Bandwidth: {self.bandwidth_display}")

        if self.burst_limit:
            config_parts.append(f"Burst: {self.burst_display}")

        if self.logical_interface_policer:
            config_parts.append("Logical Interface Policer")

        return "; ".join(config_parts) if config_parts else "No limits configured"


class JuniperFirewallPolicerAction(PrimaryModel):
    """
    Represents an action within a Juniper firewall policer configuration.

    This model defines individual actions that can be applied by a firewall policer.
    Multiple actions can belong to a single policer and are processed in order.
    Actions determine what happens to traffic when it hits the policer limits.
    """

    policer = models.ForeignKey(
        JuniperFirewallPolicer,
        on_delete=models.CASCADE,
        related_name="actions",
        help_text="The firewall policer this action belongs to",
    )

    action_type = models.CharField(
        max_length=50,
        choices=JuniperFirewallPolicerActionTypeChoices.choices,
        help_text="Type of action to apply when policer is triggered",
    )

    value = models.CharField(
        max_length=255,
        blank=True,
        help_text="Optional value for the action (used with certain action types like forwarding-class)",
    )

    order = models.IntegerField(
        default=0,
        help_text="Order in which this action is processed within the policer",
    )

    class Meta:
        """Meta class for JuniperFirewallPolicerAction model."""

        ordering = ["policer", "order", "action_type"]
        verbose_name = "Juniper Firewall Policer Action"
        verbose_name_plural = "Juniper Firewall Policer Actions"

    def __str__(self):
        """Return string representation of the policer action."""
        value_str = f": {self.value}" if self.value else ""
        return f"{self.policer.name} - {self.action_type}{value_str} (order: {self.order})"

    def clean(self):
        """Validate the policer action configuration."""
        super().clean()

        # Validate that certain action types require values
        value_required_actions = [
            JuniperFirewallPolicerActionTypeChoices.LOSS_PRIORITY,
            JuniperFirewallPolicerActionTypeChoices.FORWARDING_CLASS,
        ]

        if self.action_type in value_required_actions and not self.value:
            action_display = self.action_type
            raise ValidationError({"value": f"Action type '{action_display}' requires a value to be specified."})

        # Validate that certain action types should not have values
        value_not_allowed_actions = [
            JuniperFirewallPolicerActionTypeChoices.ACCEPT,
            JuniperFirewallPolicerActionTypeChoices.DISCARD,
            JuniperFirewallPolicerActionTypeChoices.REJECT,
            JuniperFirewallPolicerActionTypeChoices.COUNT,
            JuniperFirewallPolicerActionTypeChoices.NEXT_TERM,
        ]

        if self.action_type in value_not_allowed_actions and self.value:
            action_display = self.action_type
            raise ValidationError({"value": f"Action type '{action_display}' should not have a value specified."})

        # Validate loss priority values
        if self.action_type == JuniperFirewallPolicerActionTypeChoices.LOSS_PRIORITY and self.value:
            valid_priorities = ["low", "medium-low", "medium-high", "high"]
            if self.value.lower() not in valid_priorities:
                raise ValidationError(
                    {"value": f"Loss priority must be one of: {', '.join(valid_priorities)}. " f"Got: {self.value}"}
                )

    @property
    def requires_value(self):
        """Return whether this action type requires a value."""
        value_required_actions = [
            JuniperFirewallPolicerActionTypeChoices.LOSS_PRIORITY,
            JuniperFirewallPolicerActionTypeChoices.FORWARDING_CLASS,
        ]
        return self.action_type in value_required_actions

    @property
    def allows_value(self):
        """Return whether this action type allows a value."""
        value_not_allowed_actions = [
            JuniperFirewallPolicerActionTypeChoices.ACCEPT,
            JuniperFirewallPolicerActionTypeChoices.DISCARD,
            JuniperFirewallPolicerActionTypeChoices.REJECT,
            JuniperFirewallPolicerActionTypeChoices.COUNT,
            JuniperFirewallPolicerActionTypeChoices.NEXT_TERM,
        ]
        return self.action_type not in value_not_allowed_actions


class JuniperFirewallFilterAction(PrimaryModel):
    """
    Represents an action within a Juniper firewall filter term.

    This model defines individual actions that can be taken when a firewall
    term matches traffic. Actions include accepting, discarding, rejecting,
    counting, applying policers, or routing to specific instances.
    """

    action_type = models.CharField(
        max_length=50,
        choices=JuniperFirewallFilterActionTypeChoices.choices,
        help_text="Type of action to take when term matches",
    )

    value = models.CharField(max_length=255, blank=True, help_text="Optional value for actions that require parameters")

    order = models.IntegerField(default=0, help_text="Order in which this action is processed within the term")

    term = models.ForeignKey(
        JuniperFirewallTerm,
        on_delete=models.CASCADE,
        related_name="actions",
        help_text="The firewall term this action belongs to",
    )

    policer = models.ForeignKey(
        JuniperFirewallPolicer,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="filter_actions",
        help_text="Policer to apply when action_type is 'policer'",
    )

    # routing_instance_id = models.UUIDField(
    #     null=True,
    #     blank=True,
    #     help_text="UUID of routing instance when action_type is 'routing-instance'",
    # )

    class Meta:
        """Meta class for JuniperFirewallFilterAction model."""

        ordering = ["term", "order", "action_type"]
        verbose_name = "Juniper Firewall Filter Action"
        verbose_name_plural = "Juniper Firewall Filter Actions"

    def __str__(self):
        """Return string representation of the firewall filter action."""
        action_display = self.get_action_type_display()
        value_str = f" - {self.value}" if self.value else ""
        return f"{self.term.name}: {action_display}{value_str} (order: {self.order})"

    def clean(self):
        """Validate the firewall filter action configuration."""
        super().clean()

        # Validate that policer action requires a policer
        if self.action_type == JuniperFirewallFilterActionTypeChoices.POLICER and not self.policer:
            raise ValidationError({"policer": "Action type 'policer' requires a policer to be specified."})

        # Validate that routing-instance action requires a routing instance ID
        # if self.action_type == JuniperFirewallFilterActionTypeChoices.ROUTING_INSTANCE and not self.routing_instance_id:
        #     raise ValidationError({"routing_instance_id": "Action type 'routing-instance' requires a routing instance ID to be specified."})

        # Validate that non-policer actions should not have a policer specified
        if self.action_type != JuniperFirewallFilterActionTypeChoices.POLICER and self.policer:
            raise ValidationError({"policer": f"Action type '{self.action_type}' should not have a policer specified."})

        # Validate that non-routing-instance actions should not have a routing instance ID
        # if self.action_type != JuniperFirewallFilterActionTypeChoices.ROUTING_INSTANCE and self.routing_instance_id:
        #     raise ValidationError({"routing_instance_id": f"Action type '{self.action_type}' should not have a routing instance ID specified."})

    @property
    def requires_policer(self):
        """Return whether this action type requires a policer."""
        return self.action_type == JuniperFirewallFilterActionTypeChoices.POLICER

    @property
    def requires_routing_instance(self):
        """Return whether this action type requires a routing instance ID."""
        return self.action_type == JuniperFirewallFilterActionTypeChoices.ROUTING_INSTANCE
