using System.Text.Json;

namespace EMIC.Core.Storage;

public enum WidgetDisplayMode
{
    Taskbar,
    Tray,
    Both,
}

public sealed class AppSettingsStore
{
    private readonly string _settingsPath;
    private AppSettings _cached = new();

    public AppSettingsStore(string? rootDirectory = null)
    {
        var root = rootDirectory ?? Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
            "EMIC");
        Directory.CreateDirectory(root);
        _settingsPath = Path.Combine(root, "settings.json");
        _cached = LoadInternal();
    }

    public string? GetServerUrl() => _cached.ServerUrl;

    public string? GetSelectedSiteId() => _cached.SelectedSiteId;

    public int GetRefreshIntervalSeconds() => _cached.RefreshIntervalSeconds is > 0 and <= 600
        ? _cached.RefreshIntervalSeconds
        : 60;

    public WidgetDisplayMode GetDisplayMode()
        => Enum.TryParse<WidgetDisplayMode>(_cached.DisplayMode, out var mode) ? mode : WidgetDisplayMode.Both;

    public double GetTaskbarChipOffsetX() => _cached.TaskbarChipOffsetX >= 0 ? _cached.TaskbarChipOffsetX : 8;

    public void Save(
        string serverUrl,
        string? selectedSiteId,
        int refreshIntervalSeconds = 60,
        WidgetDisplayMode? displayMode = null,
        double? taskbarChipOffsetX = null)
    {
        _cached = new AppSettings
        {
            ServerUrl = serverUrl.Trim().TrimEnd('/'),
            SelectedSiteId = string.IsNullOrWhiteSpace(selectedSiteId) ? null : selectedSiteId.Trim(),
            RefreshIntervalSeconds = refreshIntervalSeconds,
            DisplayMode = (displayMode ?? GetDisplayMode()).ToString(),
            TaskbarChipOffsetX = taskbarChipOffsetX ?? GetTaskbarChipOffsetX(),
        };
        WriteSettings();
    }

    public void SetSelectedSiteId(string? siteId)
    {
        _cached.SelectedSiteId = string.IsNullOrWhiteSpace(siteId) ? null : siteId.Trim();
        WriteSettings();
    }

    public void SetDisplayMode(WidgetDisplayMode mode)
    {
        _cached.DisplayMode = mode.ToString();
        WriteSettings();
    }

    public void SetTaskbarChipOffsetX(double offsetX)
    {
        _cached.TaskbarChipOffsetX = offsetX;
        WriteSettings();
    }

    private void WriteSettings()
    {
        File.WriteAllText(_settingsPath, JsonSerializer.Serialize(_cached, new JsonSerializerOptions { WriteIndented = true }));
    }

    public bool IsConfigured()
        => !string.IsNullOrWhiteSpace(_cached.ServerUrl);

    private AppSettings LoadInternal()
    {
        if (!File.Exists(_settingsPath))
        {
            return new AppSettings();
        }

        try
        {
            return JsonSerializer.Deserialize<AppSettings>(File.ReadAllText(_settingsPath)) ?? new AppSettings();
        }
        catch (JsonException)
        {
            return new AppSettings();
        }
    }

    private sealed class AppSettings
    {
        public string? ServerUrl { get; set; }
        public string? SelectedSiteId { get; set; }
        public int RefreshIntervalSeconds { get; set; } = 60;
        public string DisplayMode { get; set; } = WidgetDisplayMode.Both.ToString();
        public double TaskbarChipOffsetX { get; set; } = 8;
    }
}
