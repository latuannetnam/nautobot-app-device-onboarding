"""
Juniper network interface models for Nautobot CMS Core.

This module defines models for Juniper network equipment interface configurations,
specifically focusing on VLAN tagging and QinQ (double tagging) scenarios commonly
used in service provider and enterprise networks.
"""

from django.core.exceptions import ValidationError
from django.db import models
from nautobot.core.models.generics import PrimaryModel
from nautobot.dcim.models import Interface
from nautobot.ipam.models import VLAN, IPAddress, VLANGroup

from ..choices.interfaces import (
    JuniperEncapsulationChoices,
    JuniperGigetherSpeedChoices,
    JuniperInterfaceFamilyTypeChoices,
    JuniperPhysicalModeChoices,
)


class JuniperInterfaceUnit(PrimaryModel):
    """
    Represents a Juniper interface unit with VLAN configuration.

    This model extends the base Interface model to support Juniper-specific
    VLAN tagging configurations including outer and inner VLAN tags for
    QinQ (802.1ad) double tagging scenarios.
    """

    interface = models.OneToOneField(
        Interface, on_delete=models.CASCADE, unique=True, help_text="The physical interface this unit belongs to"
    )

    enabled = models.BooleanField(default=True, help_text="Whether this interface unit is administratively enabled")

    physical_mode = models.CharField(
        max_length=50,
        choices=JuniperPhysicalModeChoices.choices,
        blank=True,
        null=True,
        help_text="Physical interface VLAN tagging mode (physical interfaces only)",
    )

    encapsulation = models.CharField(
        max_length=50,
        choices=JuniperEncapsulationChoices.choices,
        blank=True,
        null=True,
        help_text="Interface unit encapsulation type",
    )

    # VLAN configuration for QinQ (double tagging) scenarios
    outer_vlan = models.ForeignKey(
        VLAN,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="juniper_outer_vlan_interfaces",
        help_text="Outer VLAN for QinQ double tagging (typically service provider VLAN)",
    )

    inner_vlan = models.ForeignKey(
        VLAN,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="juniper_inner_vlan_interfaces",
        help_text="Inner VLAN for QinQ double tagging (typically customer VLAN)",
    )

    # VLAN group references (documentation/context purposes)
    outer_vlan_range = models.ForeignKey(
        VLANGroup,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="juniper_outer_vlan_interfaces",
        help_text="VLAN group defining permitted outer VLAN range (documentation purposes)",
    )

    inner_vlan_range = models.ForeignKey(
        VLANGroup,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="juniper_inner_vlan_interfaces",
        help_text="VLAN group defining permitted inner VLAN range (documentation purposes)",
    )

    # === Physical Interface Options (gigether-options) ===
    bundle_interface = models.CharField(
        max_length=50,
        blank=True,
        help_text="Bundle interface name for LAG/aggregated ethernet (e.g., 'ae0')",
    )

    gigether_speed = models.CharField(
        max_length=20,
        choices=JuniperGigetherSpeedChoices.choices,
        blank=True,
        null=True,
        help_text="Interface speed configuration for gigether-options",
    )

    lacp_active = models.BooleanField(
        default=False,
        help_text="Enable LACP active mode for link aggregation",
    )

    class Meta:
        """Meta configuration for JuniperInterfaceUnit model."""

        verbose_name = "Juniper Interface Unit"
        verbose_name_plural = "Juniper Interface Units"
        ordering = ["interface__name"]

    def __str__(self) -> str:
        """Return string representation of the interface unit."""
        return f"Unit on {self.interface.name}"

    @property
    def is_qinq_enabled(self) -> bool:
        """
        Check if QinQ (double VLAN tagging) is configured.

        Returns:
            bool: True if both outer and inner VLAN tags are configured
        """
        return bool(self.outer_vlan and self.inner_vlan)

    @property
    def unit_number(self):
        """
        Extract the unit number from the interface name.

        For Juniper interfaces, the unit number comes after the dot.

        Examples:
        - "ae11.199" -> returns 199
        - "ge-0/0/1.0" -> returns 0
        - "ae11" -> returns None (no unit specified)

        Returns:
            int or None: The unit number if found, None otherwise
        """
        if self.interface and self.interface.name:
            interface_name = self.interface.name
            if "." in interface_name:
                try:
                    unit_part = interface_name.split(".")[-1]
                    return int(unit_part)
                except ValueError:
                    return None
        return None

    @property
    def vlan_configuration_summary(self) -> str:
        """
        Get a summary of the VLAN configuration.

        Returns:
            str: Human-readable summary of VLAN configuration
        """
        if self.is_qinq_enabled:
            return f"QinQ: Outer({self.outer_vlan.vid}) Inner({self.inner_vlan.vid})"
        elif self.outer_vlan:
            return f"Outer VLAN: {self.outer_vlan.vid}"
        elif self.inner_vlan:
            return f"Inner VLAN: {self.inner_vlan.vid}"
        else:
            return "No VLAN configuration"


class JuniperInterfaceFamily(PrimaryModel):
    """
    Represents a protocol family configuration for a Juniper interface.

    This model defines protocol family-specific settings for Juniper interfaces,
    including MTU, MPLS settings, filters, policers, and accounting configurations.
    Multiple protocol families can be configured per interface (inet, inet6, mpls, etc.).
    """

    interface = models.ForeignKey(
        Interface,
        on_delete=models.CASCADE,
        related_name="juniper_families",
        help_text="The interface this family configuration belongs to",
    )

    family_type = models.CharField(
        max_length=50,
        choices=JuniperInterfaceFamilyTypeChoices.choices,
        help_text="Protocol family type (inet, inet6, mpls, etc.)",
    )

    mtu = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Maximum transmission unit for this family",
    )

    maximum_labels = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Maximum MPLS label stack depth",
    )

    # Filter references
    filter_input = models.ForeignKey(
        "netnam_cms_core.JuniperFirewallFilter",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="input_family_interfaces",
        help_text="Input filter for traffic filtering",
    )

    filter_output = models.ForeignKey(
        "netnam_cms_core.JuniperFirewallFilter",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="output_family_interfaces",
        help_text="Output filter for traffic filtering",
    )

    # Policer references
    policer_arp = models.ForeignKey(
        "netnam_cms_core.JuniperFirewallPolicer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="arp_family_interfaces",
        help_text="ARP policer for rate limiting",
    )

    policer_input = models.ForeignKey(
        "netnam_cms_core.JuniperFirewallPolicer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="input_family_interfaces",
        help_text="Input policer for rate limiting",
    )

    policer_output = models.ForeignKey(
        "netnam_cms_core.JuniperFirewallPolicer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="output_family_interfaces",
        help_text="Output policer for rate limiting",
    )

    # Accounting settings
    accounting_source_class_input = models.BooleanField(
        default=False,
        help_text="Enable source class accounting for input traffic",
    )

    accounting_source_class_output = models.BooleanField(
        default=False,
        help_text="Enable source class accounting for output traffic",
    )

    accounting_destination_class_usage = models.BooleanField(
        default=False,
        help_text="Enable destination class usage accounting",
    )

    class Meta:
        """Meta class for JuniperInterfaceFamily model."""

        ordering = ["interface__name", "family_type"]
        verbose_name = "Juniper Interface Family"
        verbose_name_plural = "Juniper Interface Families"
        unique_together = [["interface", "family_type"]]

    def __str__(self):
        """Return string representation of the interface family."""
        return f"{self.interface.name} - {self.get_family_type_display()}"

    def clean(self):
        """Validate model constraints."""
        super().clean()

        # Validate MTU range
        if self.mtu is not None:
            if self.mtu < 64 or self.mtu > 9192:
                raise ValidationError({"mtu": "MTU must be between 64 and 9192 bytes"})

        # Validate maximum_labels range
        if self.maximum_labels is not None:
            if self.maximum_labels < 3 or self.maximum_labels > 16:
                raise ValidationError({"maximum_labels": "Maximum labels must be between 1 and 16"})

        # Validate family-specific constraints
        if self.family_type == JuniperInterfaceFamilyTypeChoices.MPLS:
            if self.maximum_labels is None:
                raise ValidationError({"maximum_labels": "Maximum labels must be specified for MPLS family"})
        else:
            if self.maximum_labels is not None:
                raise ValidationError({"maximum_labels": "Maximum labels can only be set for MPLS family"})

    @property
    def has_filters(self) -> bool:
        """Check if any filters are configured."""
        return bool(self.filter_input or self.filter_output)

    @property
    def has_policers(self) -> bool:
        """Check if any policers are configured."""
        return bool(self.policer_arp or self.policer_input or self.policer_output)

    @property
    def has_accounting(self) -> bool:
        """Check if any accounting features are enabled."""
        return (
            self.accounting_source_class_input
            or self.accounting_source_class_output
            or self.accounting_destination_class_usage
        )

    @property
    def configuration_summary(self) -> str:
        """Get a summary of the family configuration."""
        parts = []

        if self.mtu:
            parts.append(f"MTU: {self.mtu}")

        if self.maximum_labels:
            parts.append(f"Labels: {self.maximum_labels}")

        if self.has_filters:
            filter_parts = []
            if self.filter_input:
                filter_parts.append(f"In: {self.filter_input.name}")
            if self.filter_output:
                filter_parts.append(f"Out: {self.filter_output.name}")
            parts.append(f"Filters({', '.join(filter_parts)})")

        if self.has_policers:
            policer_parts = []
            if self.policer_input:
                policer_parts.append(f"In: {self.policer_input.name}")
            if self.policer_output:
                policer_parts.append(f"Out: {self.policer_output.name}")
            if self.policer_arp:
                policer_parts.append(f"ARP: {self.policer_arp.name}")
            parts.append(f"Policers({', '.join(policer_parts)})")

        if self.has_accounting:
            parts.append("Accounting enabled")

        return " | ".join(parts) if parts else "Basic configuration"


class JuniperInterfaceVRRPGroup(PrimaryModel):
    """
    Represents a VRRP (Virtual Router Redundancy Protocol) group configuration for a Juniper interface family.

    VRRP allows multiple routers to work together to provide high availability by sharing a virtual IP address.
    This model defines the VRRP group settings including priorities, timers, and authentication for Juniper devices.
    """

    family = models.ForeignKey(
        JuniperInterfaceFamily,
        on_delete=models.CASCADE,
        related_name="vrrp_groups",
        help_text="The interface family this VRRP group belongs to",
    )

    group_number = models.PositiveIntegerField(
        help_text="VRRP group identifier (1-255)",
    )

    virtual_address = models.ForeignKey(
        IPAddress,
        on_delete=models.CASCADE,
        related_name="vrrp_groups",
        help_text="Virtual IP address shared by the VRRP group",
    )

    priority = models.PositiveIntegerField(
        default=100,
        help_text="Router priority in VRRP group (1-254, higher values have higher priority)",
    )

    hold_time = models.PositiveIntegerField(
        default=3,
        help_text="Advertisement interval in seconds (1-40)",
    )

    accept_data = models.BooleanField(
        default=False,
        help_text="Accept packets destined to virtual IP when not master",
    )

    authentication_key_chain = models.CharField(
        max_length=255,
        blank=True,
        help_text="Authentication key chain name for VRRP security",
    )

    class Meta:
        """Meta class for JuniperInterfaceVRRPGroup model."""

        ordering = ["family__interface__name", "group_number"]
        verbose_name = "Juniper Interface VRRP Group"
        verbose_name_plural = "Juniper Interface VRRP Groups"
        unique_together = [["family", "group_number"]]

    def __str__(self):
        """Return string representation of the VRRP group."""
        return f"{self.family.interface.name} VRRP Group {self.group_number} ({self.virtual_address})"

    def clean(self):
        """Validate model constraints."""
        super().clean()

        # Validate group number range
        if self.group_number < 1 or self.group_number > 255:
            raise ValidationError({"group_number": "VRRP group number must be between 1 and 255"})

        # Validate priority range
        if self.priority < 1 or self.priority > 254:
            raise ValidationError({"priority": "VRRP priority must be between 1 and 254"})

        # Validate hold time range
        if self.hold_time < 1 or self.hold_time > 40:
            raise ValidationError({"hold_time": "VRRP hold time must be between 1 and 40 seconds"})

        # Validate that the virtual address belongs to the same IP family as the interface family
        if self.virtual_address and self.family:
            if self.family.family_type == JuniperInterfaceFamilyTypeChoices.INET:
                if self.virtual_address.ip_version != 4:
                    raise ValidationError({"virtual_address": "IPv4 address required for inet family"})
            elif self.family.family_type == JuniperInterfaceFamilyTypeChoices.INET6:
                if self.virtual_address.ip_version != 6:
                    raise ValidationError({"virtual_address": "IPv6 address required for inet6 family"})

    @property
    def is_master_priority(self) -> bool:
        """Check if this router has master priority (priority = 255)."""
        return self.priority == 255

    @property
    def is_backup_priority(self) -> bool:
        """Check if this router has backup priority (priority < 100)."""
        return self.priority < 100

    @property
    def has_authentication(self) -> bool:
        """Check if authentication is configured."""
        return bool(self.authentication_key_chain.strip())

    @property
    def configuration_summary(self) -> str:
        """Get a summary of the VRRP group configuration."""
        parts = [
            f"Group {self.group_number}",
            f"VIP: {self.virtual_address}",
            f"Priority: {self.priority}",
            f"Hold: {self.hold_time}s",
        ]

        if self.accept_data:
            parts.append("Accept Data")

        if self.has_authentication:
            parts.append(f"Auth: {self.authentication_key_chain}")

        return " | ".join(parts)


class VRRPTrackRoute(PrimaryModel):
    """
    Represents a route tracking configuration for VRRP groups.

    This model defines routes that VRRP groups monitor to dynamically adjust their priority
    based on route availability. When a tracked route becomes unavailable, the VRRP router's
    priority is decremented by the specified cost, potentially causing a failover.
    """

    vrrp_group = models.ForeignKey(
        JuniperInterfaceVRRPGroup,
        on_delete=models.CASCADE,
        related_name="tracked_routes",
        help_text="The VRRP group that tracks this route",
    )

    track_id = models.PositiveIntegerField(
        help_text="Unique track identifier within the VRRP group (1-255)",
    )

    route_address = models.ForeignKey(
        IPAddress,
        on_delete=models.CASCADE,
        related_name="vrrp_trackers",
        help_text="Route address/prefix to monitor for availability",
    )

    priority_cost = models.PositiveIntegerField(
        default=10,
        help_text="Priority decrement when route becomes unavailable (1-253)",
    )

    routing_instance = models.CharField(
        max_length=255,
        blank=True,
        help_text="VRF/routing instance name where the route is located",
    )

    class Meta:
        """Meta class for VRRPTrackRoute model."""

        ordering = ["vrrp_group__family__interface__name", "vrrp_group__group_number", "track_id"]
        verbose_name = "VRRP Track Route"
        verbose_name_plural = "VRRP Track Routes"
        unique_together = [["vrrp_group", "track_id"]]

    def __str__(self):
        """Return string representation of the track route."""
        instance_info = f" in {self.routing_instance}" if self.routing_instance else ""
        return f"Track {self.track_id}: {self.route_address}{instance_info} (cost: {self.priority_cost})"

    def clean(self):
        """Validate model constraints."""
        super().clean()

        # Validate track ID range
        if self.track_id < 1 or self.track_id > 255:
            raise ValidationError({"track_id": "Track ID must be between 1 and 255"})

        # Validate priority cost range
        if self.priority_cost < 1 or self.priority_cost > 253:
            raise ValidationError({"priority_cost": "Priority cost must be between 1 and 253"})

        # Validate that priority cost doesn't make VRRP priority go below 1
        if self.vrrp_group:
            min_priority_after_decrement = self.vrrp_group.priority - self.priority_cost
            if min_priority_after_decrement < 1:
                raise ValidationError(
                    {
                        "priority_cost": f"Priority cost {self.priority_cost} would reduce VRRP priority "
                        f"below 1 (current: {self.vrrp_group.priority})"
                    }
                )

    @property
    def effective_priority_when_down(self) -> int:
        """Calculate the effective VRRP priority when this route is down."""
        return max(1, self.vrrp_group.priority - self.priority_cost)

    @property
    def has_routing_instance(self) -> bool:
        """Check if a routing instance/VRF is specified."""
        return bool(self.routing_instance.strip())

    @property
    def tracking_summary(self) -> str:
        """Get a summary of the route tracking configuration."""
        parts = [
            f"Track {self.track_id}",
            f"Route: {self.route_address}",
            f"Cost: {self.priority_cost}",
        ]

        if self.has_routing_instance:
            parts.append(f"VRF: {self.routing_instance}")

        parts.append(f"Effective Priority: {self.effective_priority_when_down}")

        return " | ".join(parts)
