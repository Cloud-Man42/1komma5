namespace EMIC.Core.Models;

public sealed class WidgetSitesResponse
{
    public string ApiVersion { get; set; } = "1.0";
    public List<WidgetSiteListItem> Sites { get; set; } = [];
}

public sealed class WidgetSiteListItem
{
    public string Id { get; set; } = string.Empty;
    public string Name { get; set; } = string.Empty;
    public string Timezone { get; set; } = string.Empty;
    public string SystemStatus { get; set; } = string.Empty;
}

public sealed class WidgetStatusResponse
{
    public string ApiVersion { get; set; } = "1.0";
    public WidgetSiteRef Site { get; set; } = new();
    public WidgetSolarSection Solar { get; set; } = new();
    public WidgetHouseSection House { get; set; } = new();
    public WidgetBatterySection Battery { get; set; } = new();
    public WidgetGridSection Grid { get; set; } = new();
    public WidgetEvSection Ev { get; set; } = new();
    public WidgetEconomySection Economy { get; set; } = new();
    public WidgetSmartChargingSection? SmartCharging { get; set; }
    public WidgetEmicSection Emic { get; set; } = new();
    public string SystemStatus { get; set; } = string.Empty;
    public DateTimeOffset? UpdatedAt { get; set; }
    public int? DataAgeSeconds { get; set; }
    public bool IsStale { get; set; }
}

public sealed class WidgetSiteRef
{
    public string Id { get; set; } = string.Empty;
    public string Name { get; set; } = string.Empty;
}

public sealed class WidgetSolarSection
{
    public double? PowerKw { get; set; }
    public double? TodayKwh { get; set; }
}

public sealed class WidgetHouseSection
{
    public double? PowerKw { get; set; }
    public double? TodayKwh { get; set; }
}

public sealed class WidgetBatterySection
{
    public double? SocPercent { get; set; }
    public double? PowerKw { get; set; }
    public string State { get; set; } = string.Empty;
    public string? StateText { get; set; }
}

public sealed class WidgetGridSection
{
    public double? PowerKw { get; set; }
    public string? Direction { get; set; }
    public double? ImportPowerKw { get; set; }
    public double? ExportPowerKw { get; set; }
}

public sealed class WidgetEvSection
{
    public string State { get; set; } = string.Empty;
    public string? StateText { get; set; }
    public double? PowerKw { get; set; }
    public double? EnergyTodayKwh { get; set; }
}

public sealed class WidgetEconomySection
{
    public double? SavedTodaySek { get; set; }
    public double? SavedMonthSek { get; set; }
    public string EconomicDataQuality { get; set; } = "unavailable";
}

public sealed class WidgetSmartChargingSection
{
    public string? Mode { get; set; }
    public string? State { get; set; }
    public string? DecisionText { get; set; }
}

public sealed class WidgetEmicSection
{
    public string? Mode { get; set; }
    public string DecisionText { get; set; } = string.Empty;
}

public sealed class WidgetSummaryResponse
{
    public string ApiVersion { get; set; } = "1.0";
    public List<WidgetStatusResponse> Sites { get; set; } = [];
    public WidgetSummaryTotals Totals { get; set; } = new();
    public DateTimeOffset? UpdatedAt { get; set; }
    public int? DataAgeSeconds { get; set; }
    public bool IsStale { get; set; }
}

public sealed class WidgetSummaryTotals
{
    public double? SolarPowerKw { get; set; }
    public double? HousePowerKw { get; set; }
    public double? BatteryStoredKwh { get; set; }
    public double? SavedTodaySek { get; set; }
}

public sealed class WidgetMeResponse
{
    public string ApiVersion { get; set; } = "1.0";
    public int DeviceId { get; set; }
    public string OwnerLabel { get; set; } = string.Empty;
    public string DeviceName { get; set; } = string.Empty;
    public string DeviceType { get; set; } = string.Empty;
    public string? DefaultSiteSlug { get; set; }
    public List<string> Scopes { get; set; } = [];
    public DateTimeOffset? LastSeenAt { get; set; }
}
