using System.Text.Json;
using EMIC.Core.Models;
using EMIC.Core.Services;
using EMIC.Core.Storage;

namespace EMIC.Core.Tests;

public class WidgetModelsTests
{
    [Fact]
    public void Deserialize_widget_status_fixture_matches_contract()
    {
        var fixturePath = ResolveFixturePath("widget-status-akarp.json");
        var json = File.ReadAllText(fixturePath);
        var status = JsonSerializer.Deserialize<WidgetStatusResponse>(json, new JsonSerializerOptions
        {
            PropertyNameCaseInsensitive = true,
        });

        Assert.NotNull(status);
        Assert.Equal("1.0", status!.ApiVersion);
        Assert.Equal("akarp", status.Site.Id);
        Assert.Equal("Åkarp", status.Site.Name);
        Assert.Equal(5.42, status.Solar.PowerKw);
        Assert.Equal(74.0, status.Battery.SocPercent);
        Assert.Equal("export", status.Grid.Direction);
        Assert.Equal("Säljer solelöverskott", status.Emic.DecisionText);
        Assert.Equal("online", status.SystemStatus);
        Assert.False(status.IsStale);
    }

    [Fact]
    public void TokenStore_roundtrip_protects_token()
    {
        var root = Path.Combine(Path.GetTempPath(), "emic-tests-" + Guid.NewGuid());
        Directory.CreateDirectory(root);
        try
        {
            var store = new TokenStore(root);
            store.SaveToken("emic_test_token_value");
            Assert.Equal("emic_test_token_value", store.LoadToken());
            store.ClearToken();
            Assert.Null(store.LoadToken());
        }
        finally
        {
            Directory.Delete(root, recursive: true);
        }
    }

    [Fact]
    public void AppSettingsStore_persists_server_url()
    {
        var root = Path.Combine(Path.GetTempPath(), "emic-settings-" + Guid.NewGuid());
        Directory.CreateDirectory(root);
        try
        {
            var store = new AppSettingsStore(root);
            store.Save("http://192.168.50.54", "akarp");
            Assert.True(store.IsConfigured());
            Assert.Equal("http://192.168.50.54", store.GetServerUrl());
            Assert.Equal("akarp", store.GetSelectedSiteId());
        }
        finally
        {
            Directory.Delete(root, recursive: true);
        }
    }

    private static string ResolveFixturePath(string fileName)
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir != null)
        {
            var candidate = Path.Combine(dir.FullName, "apple", "Fixtures", fileName);
            if (File.Exists(candidate))
            {
                return candidate;
            }

            candidate = Path.Combine(dir.FullName, "..", "apple", "Fixtures", fileName);
            if (File.Exists(candidate))
            {
                return Path.GetFullPath(candidate);
            }

            dir = dir.Parent;
        }

        throw new FileNotFoundException($"Fixture not found: {fileName}");
    }
}

public class EnergyFormatterTests
{
    [Fact]
    public void FormatPowerKw_null_returns_dash()
    {
        Assert.Equal("—", EnergyFormatter.FormatPowerKw(null));
    }

    [Fact]
    public void FormatPowerKw_formats_swedish_decimal()
    {
        Assert.Equal("5,4 kW", EnergyFormatter.FormatPowerKw(5.4));
    }

    [Fact]
    public void BuildTaskbarChipText_formats_compact_status()
    {
        var status = new WidgetStatusResponse
        {
            Site = new WidgetSiteRef { Name = "Åkarp" },
            Solar = new WidgetSolarSection { PowerKw = 5.4 },
            Battery = new WidgetBatterySection { SocPercent = 74 },
        };

        var text = EnergyFormatter.BuildTaskbarChipText(status);
        Assert.Contains("Åkarp", text);
        Assert.Contains("5,4 kW", text);
        Assert.Contains("74 %", text);
    }

    [Fact]
    public void BuildTrayTooltip_includes_site_and_power()
    {
        var status = new WidgetStatusResponse
        {
            Site = new WidgetSiteRef { Name = "Åkarp" },
            Solar = new WidgetSolarSection { PowerKw = 3.2 },
            Battery = new WidgetBatterySection { SocPercent = 70, PowerKw = 0 },
        };

        var tooltip = EnergyFormatter.BuildTrayTooltip(status);
        Assert.Contains("Åkarp", tooltip);
        Assert.Contains("3,2 kW", tooltip);
        Assert.Contains("70 %", tooltip);
    }
}
