"""
Juniper static routing models for Nautobot CMS Core.

This module defines models for Juniper static route configurations,
including support for simple and qualified next-hops, route preferences,
and community associations.
"""

from django.core.exceptions import ValidationError
from django.db import models
from nautobot.core.models.generics import PrimaryModel
from nautobot.dcim.models import Interface
from nautobot.ipam.models import IPAddress, Prefix


class JuniperStaticRoute(PrimaryModel):
    """
    Represents a Juniper static route configuration.

    This model defines static routes with support for multiple next-hop types,
    administrative distance, metrics, and various route behaviors like discard,
    reject, and community associations.
    """

    enabled = models.BooleanField(default=True, help_text="Enable or disable this static route")

    destination = models.ForeignKey(
        Prefix,
        on_delete=models.CASCADE,
        related_name="juniper_static_routes",
        help_text="Destination network prefix for this static route",
    )

    preference = models.PositiveIntegerField(
        default=5,
        help_text="Administrative distance/preference for this route (lower values are preferred)",
    )

    metric = models.PositiveIntegerField(
        default=1,
        help_text="Route metric value",
    )

    retained = models.BooleanField(
        default=False,
        help_text="Retain route in routing table when interface goes down",
    )

    readvertised = models.BooleanField(
        default=False,
        help_text="Readvertise this route to routing protocols",
    )

    resolved = models.BooleanField(
        default=True,
        help_text="Allow recursive resolution of next-hop addresses",
    )

    discarded = models.BooleanField(
        default=False,
        help_text="Discard traffic to this destination silently",
    )

    rejected = models.BooleanField(
        default=False,
        help_text="Reject traffic to this destination with ICMP unreachable",
    )

    # Optional community association for BGP redistribution
    community = models.ForeignKey(
        "netnam_cms_core.JuniperPolicyCommunity",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="static_routes",
        help_text="BGP community to associate with this static route",
    )

    class Meta:
        """Meta options for JuniperStaticRoute model."""

        ordering = ["destination", "preference"]
        verbose_name = "Juniper Static Route"
        verbose_name_plural = "Juniper Static Routes"
        unique_together = [["destination", "preference"]]

    def __str__(self) -> str:
        """Return string representation of the static route."""
        return f"{self.destination} via next-hop (preference: {self.preference})"

    def clean(self) -> None:
        """Validate static route configuration."""
        super().clean()

        # Validate mutually exclusive actions
        exclusive_actions = [self.discarded, self.rejected]
        if sum(exclusive_actions) > 1:
            raise ValidationError("Only one of discard or reject can be enabled for a static route.")

        # If discard or reject is enabled, resolve should be disabled
        if (self.discarded or self.rejected) and self.resolved:
            raise ValidationError("Resolve option cannot be enabled when discard or reject is configured.")

    @property
    def action_type(self) -> str:
        """Return the action type for this static route."""
        if self.discarded:
            return "discard"
        elif self.rejected:
            return "reject"
        else:
            return "forward"

    @property
    def has_next_hops(self) -> bool:
        """Check if this route has any configured next-hops."""
        return self.simple_next_hops.exists() or self.qualified_next_hops.exists()


class JuniperStaticRouteNexthop(PrimaryModel):
    """
    Represents a simple next-hop for a Juniper static route.

    Simple next-hops only specify an IP address and are used for
    basic static routing scenarios.
    """

    route = models.ForeignKey(
        JuniperStaticRoute,
        on_delete=models.CASCADE,
        related_name="simple_next_hops",
        help_text="The static route this next-hop belongs to",
    )

    ip_address = models.ForeignKey(
        IPAddress,
        on_delete=models.CASCADE,
        related_name="static_route_simple_next_hops",
        help_text="Next-hop IP address",
    )

    class Meta:
        """Meta options for JuniperStaticRouteNexthop model."""

        ordering = ["route", "ip_address"]
        verbose_name = "Juniper Static Route Next-hop"
        verbose_name_plural = "Juniper Static Route Next-hops"
        unique_together = [["route", "ip_address"]]

    def __str__(self) -> str:
        """Return string representation of the next-hop."""
        return f"{self.route.destination} -> {self.ip_address}"

    def clean(self) -> None:
        """Validate next-hop configuration."""
        super().clean()

        # Validate that the route doesn't have discard/reject actions
        if hasattr(self, "route") and self.route:
            if self.route.discarded or self.route.rejected:
                raise ValidationError("Cannot add next-hops to routes with discard or reject actions.")


class JuniperStaticRouteQualifiedNexthop(PrimaryModel):
    """
    Represents a qualified next-hop for a Juniper static route.

    Qualified next-hops specify both an IP address and an egress interface,
    providing more precise routing control and support for multi-homed scenarios.
    """

    route = models.ForeignKey(
        JuniperStaticRoute,
        on_delete=models.CASCADE,
        related_name="qualified_next_hops",
        help_text="The static route this qualified next-hop belongs to",
    )

    ip_address = models.ForeignKey(
        IPAddress,
        on_delete=models.CASCADE,
        related_name="static_route_qualified_next_hops",
        help_text="Next-hop IP address",
    )

    interface = models.ForeignKey(
        Interface,
        on_delete=models.CASCADE,
        related_name="static_route_qualified_next_hops",
        help_text="Egress interface for this next-hop",
    )

    class Meta:
        """Meta options for JuniperStaticRouteQualifiedNexthop model."""

        ordering = ["route", "interface", "ip_address"]
        verbose_name = "Juniper Static Route Qualified Next-hop"
        verbose_name_plural = "Juniper Static Route Qualified Next-hops"
        unique_together = [["route", "ip_address", "interface"]]

    def __str__(self) -> str:
        """Return string representation of the qualified next-hop."""
        return f"{self.route.destination} -> {self.ip_address} via {self.interface}"

    def clean(self) -> None:
        """Validate qualified next-hop configuration."""
        super().clean()

        # Validate that the route doesn't have discard/reject actions
        if hasattr(self, "route") and self.route:
            if self.route.discarded or self.route.rejected:
                raise ValidationError("Cannot add next-hops to routes with discard or reject actions.")

        # Validate that the IP address and interface are compatible
        # This could include checking if the interface has an IP in the same subnet
        # as the next-hop, but that validation might be too strict for some use cases
