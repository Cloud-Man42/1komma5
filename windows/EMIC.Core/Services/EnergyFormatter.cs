using System.Globalization;
using EMIC.Core.Models;

namespace EMIC.Core.Services;

public static class EnergyFormatter
{
    private static readonly CultureInfo Swedish = CultureInfo.GetCultureInfo("sv-SE");

    public static string FormatPowerKw(double? valueKw)
    {
        if (valueKw is null)
        {
            return "—";
        }

        return $"{valueKw.Value.ToString("0.0", Swedish)} kW";
    }

    public static string FormatSocPercent(double? value)
    {
        if (value is null)
        {
            return "—";
        }

        return $"{value.Value.ToString("0", Swedish)} %";
    }

    public static string FormatSavedSek(double? value)
    {
        if (value is null)
        {
            return "—";
        }

        return $"{value.Value.ToString("0.00", Swedish)} kr";
    }

    public static string FormatAgeSeconds(int? seconds)
    {
        if (seconds is null)
        {
            return "Okänd ålder";
        }

        if (seconds < 60)
        {
            return $"Uppdaterad för {seconds} s sedan";
        }

        var minutes = seconds.Value / 60;
        return $"Uppdaterad för {minutes} min sedan";
    }

    public static string BuildTaskbarChipText(WidgetStatusResponse? status, string? errorMessage = null)
    {
        if (!string.IsNullOrWhiteSpace(errorMessage))
        {
            return $"EMIC — {errorMessage}";
        }

        if (status == null)
        {
            return "EMIC — …";
        }

        var solar = FormatPowerKw(status.Solar.PowerKw);
        var battery = FormatSocPercent(status.Battery.SocPercent);
        return $"{status.Site.Name}  Sol {solar}  Bat {battery}";
    }

    public static string BuildTrayTooltip(WidgetStatusResponse? status, string? errorMessage = null)
    {
        if (!string.IsNullOrWhiteSpace(errorMessage))
        {
            return $"EMIC — {errorMessage}";
        }

        if (status == null)
        {
            return "EMIC — Ingen data";
        }

        var solar = FormatPowerKw(status.Solar.PowerKw);
        var battery = status.Battery.SocPercent is null
            ? "—"
            : $"{FormatSocPercent(status.Battery.SocPercent)} ({FormatPowerKw(status.Battery.PowerKw)})";
        return $"{status.Site.Name}: Sol {solar}, Batteri {battery}";
    }

    public static string GridLabel(WidgetGridSection grid)
    {
        return grid.Direction switch
        {
            "import" => "Import",
            "export" => "Export",
            _ => "Nät",
        };
    }
}
