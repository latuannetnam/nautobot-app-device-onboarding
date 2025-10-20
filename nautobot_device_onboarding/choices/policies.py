"""Policy-related models for network device configurations.

This module contains Django models that define policy configurations
and related network policy components for Juniper devices.
"""

import ipaddress
import re
from typing import List

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.functional import cached_property
from nautobot.core.models.generics import PrimaryModel

from ..choices.policies import JPSActionTypeChoices, JPSMatchConditionTypeChoices, JPSRouteFilterMatchTypeChoices

# Custom validators for reuse across models


def validate_ip_address(value):
    """Validate IP address format (IPv4 or IPv6)."""
    try:
        ipaddress.ip_address(value)
    except (ipaddress.AddressValueError, ValueError) as e:
        raise ValidationError(f"Invalid IP address format '{value}': {str(e)}") from e


def validate_community_format(value):
    """Validate BGP community format (AS:value)."""
    if not re.match(r"^\d+:\d+$", value):
        raise ValidationError(f"Invalid community format '{value}'. Expected format: 'AS:value' (e.g., '65000:100')")


def validate_as_path_regex(value):
    """Validate AS path regular expression pattern."""
    try:
        re.compile(value)
    except re.error as e:
        raise ValidationError(f"Invalid regular expression pattern '{value}': {str(e)}") from e

    # Validate characters used in AS path patterns
    if not re.match(r"^[0-9_\s()\[\].*+?^$|\\-]+$", value):
        raise ValidationError(
            "AS path pattern contains invalid characters. Use only numbers, underscores, spaces, and regex metacharacters."
        )


def validate_local_preference(value):
    """Validate BGP local preference value."""
    try:
        pref_value = int(value)
        if pref_value < 0 or pref_value > 4294967295:  # 32-bit unsigned integer
            raise ValidationError("Local preference must be between 0 and 4294967295.")
    except ValueError as e:
        raise ValidationError("Local preference must be a valid integer.") from e


# Mixin for common field cleaning patterns
class FieldCleaningMixin:
    """Mixin providing common field cleaning functionality."""

    def clean_fields(self, exclude=None):
        """Enhanced field cleaning with automatic whitespace trimming."""
        super().clean_fields(exclude)

        # Auto-trim text fields
        for field in self._meta.fields:
            if field.name not in (exclude or []) and isinstance(field, (models.CharField, models.TextField)):
                value = getattr(self, field.name)
                if value:
                    cleaned_value = value.strip()
                    setattr(self, field.name, cleaned_value)

    def _validate_field_not_empty(self, field_name: str, error_message: str = None) -> None:
        """Validate that a field is not empty or whitespace-only."""
        value = getattr(self, field_name)
        if not value or not value.strip():
            error_message = error_message or f"{field_name.title()} cannot be empty."
            raise ValidationError({field_name: error_message})


# Base model for policy-related configurations
class PolicyConfigurationModelMixin(FieldCleaningMixin):
    """Base mixin for policy configuration models with common patterns."""

    def _validate_condition_type_match(self, expected_types: List[str], error_message: str = None) -> None:
        """Validate that a related condition has the expected type."""
        if hasattr(self, "match_condition") and self.match_condition:
            if self.match_condition.condition_type not in expected_types:
                error_message = error_message or (
                    f"Can only be associated with {'/'.join(expected_types)} type match conditions, "
                    f"not {self.match_condition.get_condition_type_display()}"
                )
                raise ValidationError({"match_condition": error_message})

    def _validate_action_type_match(self, expected_types: List[str], error_message: str = None) -> None:
        """Validate that a related action has the expected type."""
        if hasattr(self, "action") and self.action:
            if self.action.action_type not in expected_types:
                error_message = error_message or (
                    f"Can only be associated with {'/'.join(expected_types)} type actions, "
                    f"not {self.action.get_action_type_display()}"
                )
                raise ValidationError({"action": error_message})


class JuniperPolicyPrefixList(PolicyConfigurationModelMixin, PrimaryModel):
    """
    Represents a Juniper policy prefix list configuration.

    This model defines prefix lists used in Juniper policy configurations
    for matching IP prefixes in firewall filters and routing policies.
    Prefix lists contain multiple prefix items and can be referenced
    by firewall match conditions.
    """

    name = models.CharField(max_length=255, unique=True, help_text="Name of the prefix list")

    apply_path = models.CharField(
        max_length=255, help_text="Policy apply path where this prefix list is used", null=True, blank=True
    )

    class Meta:
        """Meta class for JuniperPolicyPrefixList model."""

        ordering = ["name"]
        verbose_name = "Juniper Policy Prefix List"
        verbose_name_plural = "Juniper Policy Prefix Lists"
        indexes = [
            models.Index(fields=["name"]),
        ]

    def __str__(self):
        """Return string representation of the prefix list."""
        return f"{self.name} ({self.apply_path})" if self.apply_path else self.name

    def clean_fields(self, exclude=None):
        """Validate Juniper naming conventions (alphanumeric, hyphens, underscores)."""
        super().clean_fields(exclude)

        if "name" not in exclude and not re.match(r"^[a-zA-Z0-9_-]+$", getattr(self, "name")):
            raise ValidationError("Name must contain only alphanumeric characters, hyphens, and underscores.")

    @property
    def prefix_count(self):
        """Return the number of prefix items in this list."""
        return self.prefix_items.count()


class JuniperPolicyPrefixItem(PolicyConfigurationModelMixin, PrimaryModel):
    """
    Represents an individual prefix item within a Juniper policy prefix list.

    This model defines specific IP prefixes that are part of a prefix list.
    Each item belongs to a single prefix list and represents a network
    prefix that can be matched in policy configurations.
    """

    prefix_list = models.ForeignKey(
        JuniperPolicyPrefixList,
        on_delete=models.CASCADE,
        related_name="prefix_items",
        help_text="The prefix list this item belongs to",
    )

    name = models.CharField(max_length=255, help_text="Name or identifier for this prefix item")

    class Meta:
        """Meta class for JuniperPolicyPrefixItem model."""

        ordering = ["prefix_list", "name"]
        verbose_name = "Juniper Policy Prefix Item"
        verbose_name_plural = "Juniper Policy Prefix Items"
        unique_together = ["prefix_list", "name"]
        indexes = [
            models.Index(fields=["prefix_list", "name"]),
        ]

    def __str__(self):
        """Return string representation of the prefix item."""
        return f"{self.prefix_list.name}::{self.name}"

    def clean(self):
        """Validate the prefix item configuration."""
        super().clean()
        self._validate_field_not_empty("name", "Prefix item name cannot be empty.")


class JuniperPolicyStatement(PolicyConfigurationModelMixin, PrimaryModel):
    """
    Model representing a Juniper network policy statement.

    A policy statement is a fundamental component in Juniper routing policies
    that defines rules for route manipulation, filtering, and modification.
    """

    name = models.CharField(max_length=255, unique=True, help_text="Unique name for the policy statement")

    description = models.CharField(
        max_length=255, blank=True, help_text="Optional description of the policy statement purpose"
    )

    class Meta:
        """Meta configuration for JuniperPolicyStatement model."""

        ordering = ["name"]
        verbose_name = "Juniper Policy Statement"
        verbose_name_plural = "Juniper Policy Statements"
        indexes = [
            models.Index(fields=["name"]),
        ]

    def __str__(self) -> str:
        """
        Return string representation of the policy statement.

        :return: The policy statement name
        :rtype: str
        """
        return self.name


class JPSTerm(PolicyConfigurationModelMixin, PrimaryModel):
    """
    Model representing a term within a Juniper policy statement.

    A policy statement term defines specific match conditions and actions
    that are evaluated in order during route processing. The is_terminal_term
    flag indicates the final term in a statement per CSDL requirements.
    """

    name = models.CharField(max_length=255, help_text="Name for the policy statement term")

    description = models.CharField(max_length=255, blank=True, help_text="Optional description of the term purpose")

    order = models.PositiveIntegerField(
        default=0,
        help_text="Execution order of the term within the policy statement",
    )

    enabled = models.BooleanField(default=True, help_text="Whether this term is active")

    statement = models.ForeignKey(
        JuniperPolicyStatement,
        on_delete=models.CASCADE,
        related_name="terms",
        help_text="The policy statement this term belongs to",
    )

    is_terminal_term = models.BooleanField(
        default=False, help_text="Marks the terminal term to open subsequent network statements per CSDL requirements"
    )

    class Meta:
        """Meta configuration for JPSTerm model."""

        ordering = ["statement", "order", "name"]
        verbose_name = "JPS Term"
        verbose_name_plural = "JPS Terms"
        unique_together = [["statement", "name"]]
        indexes = [
            models.Index(fields=["statement", "order"]),
            models.Index(fields=["enabled"]),
            models.Index(fields=["is_terminal_term"]),
        ]

    def __str__(self) -> str:
        """
        Return string representation of the term.

        :return: The term name with statement context
        :rtype: str
        """
        return f"{self.statement.name}::{self.name}"

    def save(self, *args, **kwargs):
        """
        Override save to ensure only one terminal term per statement.

        :param args: Positional arguments
        :param kwargs: Keyword arguments
        """
        if self.is_terminal_term:
            # Ensure only one terminal term per statement
            JPSTerm.objects.filter(statement=self.statement, is_terminal_term=True).exclude(pk=self.pk).update(
                is_terminal_term=False
            )

        super().save(*args, **kwargs)


class JPSMatchCondition(PolicyConfigurationModelMixin, PrimaryModel):
    """
    Model representing a match condition within a JPS term.

    Match conditions define the criteria used to filter traffic in policy
    statements, supporting various condition types like route-filter,
    protocol, prefix-list-filter, and next-hop matching.
    """

    term = models.ForeignKey(
        JPSTerm,
        on_delete=models.CASCADE,
        related_name="match_conditions",
        help_text="The JPS term this match condition belongs to",
    )

    condition_type = models.CharField(
        max_length=50,
        choices=JPSMatchConditionTypeChoices.choices,
        help_text="Type of match condition to evaluate",
    )

    order = models.PositiveIntegerField(
        help_text="Evaluation sequence for this match condition",
    )

    value = models.TextField(help_text="Condition-specific value based on the condition type")

    class Meta:
        """Meta configuration for JPSMatchCondition model."""

        ordering = ["term", "order", "condition_type"]
        verbose_name = "JPS Match Condition"
        verbose_name_plural = "JPS Match Conditions"
        unique_together = [["term", "condition_type", "order"]]
        indexes = [
            models.Index(fields=["term", "order"]),
            models.Index(fields=["condition_type"]),
        ]

    def __str__(self) -> str:
        """
        Return string representation of the match condition.

        :return: The match condition with term and type context
        :rtype: str
        """
        return f"{self.term.statement.name}::{self.term.name}::{self.condition_type}"

    def clean(self) -> None:
        """
        Perform model validation.

        :raises ValidationError: If validation fails
        """
        super().clean()
        self._validate_field_not_empty("value", "Value cannot be empty.")

    @cached_property
    def condition_type_display_cached(self) -> str:
        """
        Get cached display value for condition_type field.

        :return: The display value for the condition type
        :rtype: str
        """
        return self.get_condition_type_display()


class JPSMatchConditionRouteFilter(PolicyConfigurationModelMixin, PrimaryModel):
    """
    Model representing a route filter within a JPS match condition.

    Route filters extend route-filter type match conditions with specific
    prefix matching rules. They define IP prefixes and match operators
    that are evaluated when filtering routes in policy statements.
    """

    match_condition = models.ForeignKey(
        JPSMatchCondition,
        on_delete=models.CASCADE,
        related_name="route_filters",
        help_text="The match condition this route filter belongs to",
    )

    enable = models.BooleanField(
        default=True,
        help_text="Whether this route filter is active",
    )

    value = models.CharField(
        max_length=255,
        help_text="Route prefix/address to match (e.g., '10.0.0.0/8', '192.168.1.0/24')",
    )

    match_type = models.CharField(
        max_length=50,
        choices=JPSRouteFilterMatchTypeChoices.choices,
        blank=True,
        null=True,
        help_text="Match operator for prefix matching (exact, longer, orlonger, prefix-length range)",
    )

    class Meta:
        """Meta configuration for JPSMatchConditionRouteFilter model."""

        ordering = ["match_condition", "value"]
        verbose_name = "JPS Match Condition Route Filter"
        verbose_name_plural = "JPS Match Condition Route Filters"
        indexes = [
            models.Index(fields=["match_condition"]),
            models.Index(fields=["enable"]),
            models.Index(fields=["match_type"]),
        ]

    def __str__(self) -> str:
        """
        Return string representation of the route filter.

        :return: The route filter with match condition context
        :rtype: str
        """
        match_type_display = f" ({self.get_match_type_display()})" if self.match_type else ""
        return f"{self.match_condition}::{self.value}{match_type_display}"

    def clean_fields(self, exclude=None):
        """Validate IP network format (IPv4 or IPv6)."""
        super().clean_fields(exclude)

        try:
            value = getattr(self, "value")
            ipaddress.ip_network(value, strict=False)
        except (ipaddress.AddressValueError, ValueError) as e:
            raise ValidationError(f"Invalid IP network format '{value}': {str(e)}") from e

    def clean(self) -> None:
        """
        Perform model validation.

        :raises ValidationError: If validation fails
        """
        super().clean()

        self._validate_field_not_empty("value", "Route prefix value cannot be empty.")

        self._validate_condition_type_match(
            [JPSMatchConditionTypeChoices.ROUTE_FILTER],
            "Route filter can only be associated with route-filter type match conditions",
        )


class JPSMatchConditionPrefixList(PolicyConfigurationModelMixin, PrimaryModel):
    """
    Model representing a prefix list within a JPS match condition.

    Prefix lists extend prefix-list-filter type match conditions by
    referencing existing prefix list configurations. They define
    associations between match conditions and predefined prefix lists
    used for route filtering in policy statements.
    """

    match_condition = models.ForeignKey(
        JPSMatchCondition,
        on_delete=models.CASCADE,
        related_name="prefix_lists",
        help_text="The match condition this prefix list belongs to",
    )

    prefix_list = models.ForeignKey(
        JuniperPolicyPrefixList,
        on_delete=models.CASCADE,
        related_name="match_condition_references",
        help_text="The prefix list configuration to reference",
    )

    class Meta:
        """Meta configuration for JPSMatchConditionPrefixList model."""

        ordering = ["match_condition", "prefix_list"]
        verbose_name = "JPS Match Condition Prefix List"
        verbose_name_plural = "JPS Match Condition Prefix Lists"
        unique_together = [["match_condition", "prefix_list"]]
        indexes = [
            models.Index(fields=["match_condition"]),
            models.Index(fields=["prefix_list"]),
        ]

    def __str__(self) -> str:
        """
        Return string representation of the prefix list reference.

        :return: The prefix list reference with match condition context
        :rtype: str
        """
        return f"{self.match_condition}::{self.prefix_list.name}"

    def clean(self) -> None:
        """
        Perform model validation.

        :raises ValidationError: If validation fails
        """
        super().clean()

        self._validate_condition_type_match(
            [JPSMatchConditionTypeChoices.PREFIX_LIST_FILTER],
            "Prefix list can only be associated with prefix-list-filter type match conditions",
        )


class JuniperPolicyCommunity(PolicyConfigurationModelMixin, PrimaryModel):
    """
    Model representing a Juniper BGP policy community configuration.

    Communities are used in BGP routing policies to tag routes with
    community attributes that can be used for route filtering,
    preference setting, and other policy decisions.
    """

    name = models.CharField(max_length=255, unique=True, help_text="Unique name for the BGP community")

    members = models.CharField(
        max_length=255, blank=True, null=True, help_text="BGP community values (e.g., '65000:100', '65000:200')"
    )

    class Meta:
        """Meta configuration for JuniperPolicyCommunity model."""

        ordering = ["name"]
        verbose_name = "Juniper Policy Community"
        verbose_name_plural = "Juniper Policy Communities"
        indexes = [
            models.Index(fields=["name"]),
        ]

    def __str__(self) -> str:
        """
        Return string representation of the community.

        :return: The community name
        :rtype: str
        """
        return self.name

    def clean_fields(self, exclude=None):
        """Validate Juniper naming conventions (alphanumeric, hyphens, underscores)."""
        super().clean_fields(exclude)

        if "name" not in exclude and not re.match(r"^[a-zA-Z0-9_-]+$", getattr(self, "name")):
            raise ValidationError("Name must contain only alphanumeric characters, hyphens, and underscores.")

    def clean(self) -> None:
        """
        Perform model validation.

        :raises ValidationError: If validation fails
        """
        super().clean()

        # Validate members format if provided
        if self.members:
            self._validate_community_members()

    def _validate_community_members(self) -> None:
        """Validate community members format."""
        community_values = [value.strip() for value in self.members.split(",")]
        for value in community_values:
            if value:
                validate_community_format(value)

    @cached_property
    def member_count(self) -> int:
        """
        Return the number of community members.

        :return: Number of community values
        :rtype: int
        """
        if not self.members:
            return 0
        return len([value.strip() for value in self.members.split(",") if value.strip()])


class JPSMatchConditionCommunity(PrimaryModel):
    """
    Model representing a community within a JPS match condition.

    Communities extend community type match conditions by referencing
    existing BGP community configurations. They define associations
    between match conditions and predefined community values used
    for BGP route filtering in policy statements.
    """

    match_condition = models.ForeignKey(
        JPSMatchCondition,
        on_delete=models.CASCADE,
        related_name="communities",
        help_text="The match condition this community belongs to",
    )

    community = models.ForeignKey(
        JuniperPolicyCommunity,
        on_delete=models.CASCADE,
        related_name="match_condition_references",
        help_text="The community configuration to reference",
    )

    class Meta:
        """Meta configuration for JPSMatchConditionCommunity model."""

        ordering = ["match_condition", "community"]
        verbose_name = "JPS Match Condition Community"
        verbose_name_plural = "JPS Match Condition Communities"
        unique_together = [["match_condition", "community"]]
        indexes = [
            models.Index(fields=["match_condition"]),
            models.Index(fields=["community"]),
        ]

    def __str__(self) -> str:
        """
        Return string representation of the community reference.

        :return: The community reference with match condition context
        :rtype: str
        """
        return f"{self.match_condition}::{self.community.name}"

    def clean(self) -> None:
        """
        Perform model validation.

        :raises ValidationError: If validation fails
        """
        super().clean()

        # Validate that match_condition is of community type
        if self.match_condition and self.match_condition.condition_type != JPSMatchConditionTypeChoices.COMMUNITY:
            raise ValidationError(
                {
                    "match_condition": f"Community can only be associated with community type match conditions, "
                    f"not {self.match_condition.get_condition_type_display()}"
                }
            )


class JuniperPolicyAsPath(PrimaryModel):
    """
    Model representing a Juniper BGP AS path configuration.

    AS paths are used in BGP routing policies to match routes based
    on their autonomous system path attributes. They use regular
    expressions to match against the AS path sequence in BGP routes.
    """

    name = models.CharField(max_length=255, unique=True, help_text="Unique name for the AS path pattern")

    path = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Regular expression pattern for AS path matching (e.g., '^65000_', '.*65001.*')",
    )

    class Meta:
        """Meta configuration for JuniperPolicyAsPath model."""

        ordering = ["name"]
        verbose_name = "Juniper Policy AS Path"
        verbose_name_plural = "Juniper Policy AS Paths"
        indexes = [
            models.Index(fields=["name"]),
        ]

    def __str__(self) -> str:
        """
        Return string representation of the AS path.

        :return: The AS path name
        :rtype: str
        """
        return self.name

    def clean(self) -> None:
        """
        Perform model validation.

        :raises ValidationError: If validation fails
        """
        super().clean()

        # Ensure name is stripped of whitespace
        if self.name:
            self.name = self.name.strip()

        # Ensure path is stripped of whitespace if provided
        if self.path:
            self.path = self.path.strip()

        # Validate name follows naming conventions
        if self.name:
            if not re.match(r"^[a-zA-Z0-9_-]+$", self.name):
                raise ValidationError(
                    {"name": "AS path name must contain only alphanumeric characters, hyphens, and underscores."}
                )

        # Basic validation for AS path regular expression if provided
        if self.path:
            try:
                # Test if the path is a valid regular expression
                re.compile(self.path)
            except re.error as e:
                raise ValidationError({"path": f"Invalid regular expression pattern '{self.path}': {str(e)}"}) from e

            # Validate that path contains only valid AS path characters
            # AS paths typically contain numbers, underscores, spaces, parentheses, and common regex metacharacters
            if not re.match(r"^[0-9,_\s()\[\]{}.*+?^$|\\-]+$", self.path):
                raise ValidationError(
                    {
                        "path": f"AS path pattern '{self.path}' contains invalid characters. Use only numbers, underscores, spaces, and regex metacharacters."
                    }
                )


class JPSMatchConditionAsPath(PrimaryModel):
    """
    Model representing an AS path within a JPS match condition.

    AS paths extend as-path type match conditions by referencing
    existing BGP AS path configurations. They define associations
    between match conditions and predefined AS path patterns used
    for BGP route filtering in policy statements.
    """

    match_condition = models.ForeignKey(
        JPSMatchCondition,
        on_delete=models.CASCADE,
        related_name="as_paths",
        help_text="The match condition this AS path belongs to",
    )

    as_path = models.ForeignKey(
        JuniperPolicyAsPath,
        on_delete=models.CASCADE,
        related_name="match_condition_references",
        help_text="The AS path configuration to reference",
    )

    class Meta:
        """Meta configuration for JPSMatchConditionAsPath model."""

        ordering = ["match_condition", "as_path"]
        verbose_name = "JPS Match Condition AS Path"
        verbose_name_plural = "JPS Match Condition AS Paths"
        unique_together = [["match_condition", "as_path"]]
        indexes = [
            models.Index(fields=["match_condition"]),
            models.Index(fields=["as_path"]),
        ]

    def __str__(self) -> str:
        """
        Return string representation of the AS path reference.

        :return: The AS path reference with match condition context
        :rtype: str
        """
        return f"{self.match_condition}::{self.as_path.name}"

    def clean(self) -> None:
        """
        Perform model validation.

        :raises ValidationError: If validation fails
        """
        super().clean()

        # Validate that match_condition is of as-path type
        if self.match_condition and self.match_condition.condition_type != JPSMatchConditionTypeChoices.AS_PATH:
            raise ValidationError(
                {
                    "match_condition": f"AS path can only be associated with as-path type match conditions, "
                    f"not {self.match_condition.get_condition_type_display()}"
                }
            )


class JPSAction(PrimaryModel):
    """
    Model representing an action within a JPS term.

    Actions define what happens when a term's match conditions are met,
    such as setting BGP attributes, accepting/rejecting routes, or
    transferring control to other policies. Actions are executed in
    order sequence when their parent term matches.
    """

    term = models.ForeignKey(
        JPSTerm,
        on_delete=models.CASCADE,
        related_name="actions",
        help_text="The JPS term this action belongs to",
    )

    action_type = models.CharField(
        max_length=50,
        choices=JPSActionTypeChoices.choices,
        help_text="Type of action to execute",
    )

    value = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Action-specific value (e.g., local preference value, next-hop IP, community value)",
    )

    order = models.IntegerField(
        default=0,
        help_text="Execution sequence for this action within the term",
    )

    class Meta:
        """Meta configuration for JPSAction model."""

        ordering = ["term", "order", "action_type"]
        verbose_name = "JPS Action"
        verbose_name_plural = "JPS Actions"
        unique_together = [["term", "action_type", "order"]]
        indexes = [
            models.Index(fields=["term", "order"]),
            models.Index(fields=["action_type"]),
        ]

    def __str__(self) -> str:
        """
        Return string representation of the action.

        :return: The action with term and type context
        :rtype: str
        """
        value_display = f" ({self.value})" if self.value else ""
        return f"{self.term.statement.name}::{self.term.name}::{self.action_type}{value_display}"

    def clean(self) -> None:
        """
        Perform model validation.

        :raises ValidationError: If validation fails
        """
        super().clean()

        # Ensure value is stripped of whitespace if provided
        if self.value:
            self.value = self.value.strip()

        # Validate order is non-negative
        if self.order < 0:
            raise ValidationError({"order": "Order must be zero or positive."})

        # Validate value requirements based on action type
        if self.action_type:
            value_required_actions = [
                JPSActionTypeChoices.LOCAL_PREFERENCE,
                JPSActionTypeChoices.NEXT_HOP,
                JPSActionTypeChoices.COMMUNITY_ADD,
                JPSActionTypeChoices.COMMUNITY_DELETE,
                JPSActionTypeChoices.COMMUNITY_SET,
                JPSActionTypeChoices.AS_PATH_PREPEND,
                JPSActionTypeChoices.AS_PATH_EXPAND,
            ]

            value_forbidden_actions = [
                JPSActionTypeChoices.ACCEPT,
                JPSActionTypeChoices.REJECT,
                JPSActionTypeChoices.NEXT_POLICY,
            ]

            if self.action_type in value_required_actions and not self.value:
                raise ValidationError({"value": f"Value is required for {self.get_action_type_display()} action type."})

            if self.action_type in value_forbidden_actions and self.value:
                raise ValidationError(
                    {"value": f"Value should not be specified for {self.get_action_type_display()} action type."}
                )

        # Validate value format based on action type
        if self.value and self.action_type:
            if self.action_type == JPSActionTypeChoices.LOCAL_PREFERENCE:
                try:
                    pref_value = int(self.value)
                    if pref_value < 0 or pref_value > 4294967295:  # 32-bit unsigned integer
                        raise ValidationError({"value": "Local preference must be between 0 and 4294967295."})
                except ValueError as e:
                    raise ValidationError({"value": "Local preference must be a valid integer."}) from e

            elif self.action_type == JPSActionTypeChoices.NEXT_HOP:
                import ipaddress

                try:
                    # Validate as IPv4 or IPv6 address
                    ipaddress.ip_address(self.value)
                except (ipaddress.AddressValueError, ValueError) as e:
                    raise ValidationError({"value": f"Invalid IP address format '{self.value}': {str(e)}"}) from e

            elif self.action_type in [
                JPSActionTypeChoices.COMMUNITY_ADD,
                JPSActionTypeChoices.COMMUNITY_DELETE,
                JPSActionTypeChoices.COMMUNITY_SET,
            ]:
                # Basic validation for community format
                community_values = [value.strip() for value in self.value.split(",")]
                for value in community_values:
                    if value and not re.match(r"^\d+:\d+$", value):
                        raise ValidationError(
                            {
                                "value": f"Invalid community format '{value}'. Expected format: 'AS:value' (e.g., '65000:100')"
                            }
                        )

            elif self.action_type in [
                JPSActionTypeChoices.AS_PATH_PREPEND,
                JPSActionTypeChoices.AS_PATH_EXPAND,
            ]:
                # Basic validation for AS path format
                # AS path values should be AS numbers separated by spaces
                as_values = self.value.split()
                for as_value in as_values:
                    if as_value and not re.match(r"^\d+$", as_value):
                        raise ValidationError(
                            {
                                "value": f"Invalid AS number format '{as_value}'. Expected format: space-separated AS numbers (e.g., '65000 65001')"
                            }
                        )

    def get_action_type_display_cached(self) -> str:
        """
        Get cached display value for action_type field.

        :return: The display value for the action type
        :rtype: str
        """
        if not hasattr(self, "_action_type_display_cache") or self._action_type_display_cache is None:
            self._action_type_display_cache = self.get_action_type_display()
        return self._action_type_display_cache


class JPSActionCommunity(PrimaryModel):
    """
    Model representing a community reference within a JPS action.

    Communities extend community-related actions (add/delete/set) by
    referencing existing BGP community configurations. They define
    associations between actions and predefined community values used
    for BGP route modification in policy statements.
    """

    action = models.ForeignKey(
        JPSAction,
        on_delete=models.CASCADE,
        related_name="communities",
        help_text="The JPS action this community belongs to",
    )

    community = models.ForeignKey(
        JuniperPolicyCommunity,
        on_delete=models.CASCADE,
        related_name="action_references",
        help_text="The community configuration to reference",
    )

    class Meta:
        """Meta configuration for JPSActionCommunity model."""

        ordering = ["action", "community"]
        verbose_name = "JPS Action Community"
        verbose_name_plural = "JPS Action Communities"
        unique_together = [["action", "community"]]
        indexes = [
            models.Index(fields=["action"]),
            models.Index(fields=["community"]),
        ]

    def __str__(self) -> str:
        """
        Return string representation of the action community reference.

        :return: The community reference with action context
        :rtype: str
        """
        return f"{self.action}::{self.community.name}"

    def clean(self) -> None:
        """
        Perform model validation.

        :raises ValidationError: If validation fails
        """
        super().clean()

        # Validate that action is of community-related type
        if self.action and self.action.action_type not in [
            JPSActionTypeChoices.COMMUNITY_ADD,
            JPSActionTypeChoices.COMMUNITY_DELETE,
            JPSActionTypeChoices.COMMUNITY_SET,
        ]:
            raise ValidationError(
                {
                    "action": f"Community can only be associated with community-related action types "
                    f"(add/delete/set), not {self.action.get_action_type_display()}"
                }
            )


class JPSActionAsPath(PrimaryModel):
    """
    Model representing an AS path reference within a JPS action.

    AS paths extend AS path manipulation actions (prepend/expand) by
    referencing existing BGP AS path configurations. They define
    associations between actions and predefined AS path patterns used
    for BGP route modification in policy statements.
    """

    action = models.ForeignKey(
        JPSAction,
        on_delete=models.CASCADE,
        related_name="as_paths",
        help_text="The JPS action this AS path belongs to",
    )

    as_path = models.ForeignKey(
        JuniperPolicyAsPath,
        on_delete=models.CASCADE,
        related_name="action_references",
        help_text="The AS path configuration to reference",
    )

    class Meta:
        """Meta configuration for JPSActionAsPath model."""

        ordering = ["action", "as_path"]
        verbose_name = "JPS Action AS Path"
        verbose_name_plural = "JPS Action AS Paths"
        unique_together = [["action", "as_path"]]
        indexes = [
            models.Index(fields=["action"]),
            models.Index(fields=["as_path"]),
        ]

    def __str__(self) -> str:
        """
        Return string representation of the action AS path reference.

        :return: The AS path reference with action context
        :rtype: str
        """
        return f"{self.action}::{self.as_path.name}"

    def clean(self) -> None:
        """
        Perform model validation.

        :raises ValidationError: If validation fails
        """
        super().clean()

        # Validate that action is of AS path-related type
        if self.action and self.action.action_type not in [
            JPSActionTypeChoices.AS_PATH_PREPEND,
            JPSActionTypeChoices.AS_PATH_EXPAND,
        ]:
            raise ValidationError(
                {
                    "action": f"AS path can only be associated with AS path-related action types "
                    f"(prepend/expand), not {self.action.get_action_type_display()}"
                }
            )
