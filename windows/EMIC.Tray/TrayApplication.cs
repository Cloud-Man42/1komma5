using System.Drawing;
using Microsoft.Win32;
using System.Windows;
using System.Windows.Threading;
using EMIC.Core.Models;
using EMIC.Core.Services;
using EMIC.Core.Storage;
using EMIC.Tray.Views;
using Forms = System.Windows.Forms;

namespace EMIC.Tray;

public sealed class TrayApplication : IDisposable
{
    private readonly AppSettingsStore _settings = new();
    private readonly TokenStore _tokens = new();
    private readonly EmicApiClient _apiClient;
    private readonly Forms.NotifyIcon _notifyIcon;
    private readonly DispatcherTimer _refreshTimer;
    private readonly FlyoutWindow _flyout;
    private readonly TaskbarChipWindow _chip;
    private readonly EventHandler _displaySettingsChangedHandler;
    private WidgetStatusResponse? _latestStatus;
    private string? _latestError;
    private IReadOnlyList<WidgetSiteListItem> _sites = [];

    public TrayApplication()
    {
        _apiClient = new EmicApiClient(_settings, _tokens);
        _flyout = new FlyoutWindow();
        _flyout.SiteChanged += OnSiteChanged;
        _flyout.RefreshRequested += (_, _) => _ = RefreshAsync(showFlyout: true);
        _flyout.OpenSettingsRequested += (_, _) => ShowSetupWindow();

        _chip = new TaskbarChipWindow();
        _chip.Activated += (_, _) => _chip.DockToTaskbar(_settings.GetTaskbarChipOffsetX());
        _chip.ChipClicked += (_, _) => ToggleFlyout();
        _chip.RefreshRequested += (_, _) => _ = RefreshAsync(showFlyout: _flyout.IsVisible);
        _chip.OpenSettingsRequested += (_, _) => ShowSetupWindow();
        _chip.ExitRequested += (_, _) => Shutdown();
        _chip.ChipOffsetChanged += (_, offset) =>
        {
            _settings.SetTaskbarChipOffsetX(offset);
            _chip.DockToTaskbar(offset);
        };

        _notifyIcon = new Forms.NotifyIcon
        {
            Icon = TrayIconFactory.Create(isStale: false, isError: false),
            Text = "EMIC",
            Visible = false,
        };
        _notifyIcon.MouseClick += OnNotifyIconClick;
        _notifyIcon.ContextMenuStrip = BuildContextMenu();

        _refreshTimer = new DispatcherTimer { Interval = TimeSpan.FromSeconds(_settings.GetRefreshIntervalSeconds()) };
        _refreshTimer.Tick += (_, _) => _ = RefreshAsync(showFlyout: _flyout.IsVisible);

        _displaySettingsChangedHandler = (_, _) => DockChip();
        SystemEvents.DisplaySettingsChanged += _displaySettingsChangedHandler;

        ApplyDisplayMode();

        if (!_settings.IsConfigured() || !_tokens.HasToken())
        {
            ShowSetupWindow();
        }
        else
        {
            _refreshTimer.Start();
            _ = RefreshAsync(showFlyout: false);
        }
    }

    public void Start()
    {
    }

    private Forms.ContextMenuStrip BuildContextMenu()
    {
        var menu = new Forms.ContextMenuStrip();
        menu.Items.Add("Visa widget", null, (_, _) => ToggleFlyout());
        menu.Items.Add("Uppdatera nu", null, (_, _) => _ = RefreshAsync(showFlyout: _flyout.IsVisible));
        menu.Items.Add("Inställningar…", null, (_, _) => ShowSetupWindow());
        menu.Items.Add(new Forms.ToolStripSeparator());
        menu.Items.Add("Avsluta", null, (_, _) => Shutdown());
        return menu;
    }

    private void ApplyDisplayMode()
    {
        var mode = _settings.GetDisplayMode();
        var showTray = mode is WidgetDisplayMode.Tray or WidgetDisplayMode.Both;
        var showChip = mode is WidgetDisplayMode.Taskbar or WidgetDisplayMode.Both;

        _notifyIcon.Visible = showTray;
        _chip.ShowInTaskbar = showChip;
        if (showChip)
        {
            _chip.Show();
            DockChip();
        }
        else
        {
            _chip.Hide();
        }
    }

    private void DockChip()
    {
        _chip.DockToTaskbar(_settings.GetTaskbarChipOffsetX());
    }

    private void OnNotifyIconClick(object? sender, Forms.MouseEventArgs e)
    {
        if (e.Button == Forms.MouseButtons.Left)
        {
            ToggleFlyout();
        }
    }

    private void ToggleFlyout()
    {
        if (_flyout.IsVisible)
        {
            _flyout.Hide();
            return;
        }

        PositionFlyoutNearChip();
        _flyout.Show();
        _flyout.Activate();
        _ = RefreshAsync(showFlyout: true);
    }

    private void PositionFlyoutNearChip()
    {
        _flyout.Left = _chip.Left;
        _flyout.Top = _chip.Top - _flyout.ActualHeight - 8;
        if (_flyout.Top < SystemParameters.WorkArea.Top)
        {
            _flyout.Top = _chip.Top + _chip.ActualHeight + 8;
        }

        if (_flyout.Left + _flyout.Width > SystemParameters.WorkArea.Right - 8)
        {
            _flyout.Left = SystemParameters.WorkArea.Right - _flyout.Width - 8;
        }
    }

    private void ShowSetupWindow()
    {
        var setup = new SetupWindow(_settings, _tokens);
        setup.ShowDialog();
        if (setup.Saved)
        {
            _refreshTimer.Interval = TimeSpan.FromSeconds(_settings.GetRefreshIntervalSeconds());
            _refreshTimer.Start();
            ApplyDisplayMode();
            _ = RefreshAsync(showFlyout: false);
        }
    }

    private void OnSiteChanged(object? sender, string? siteId)
    {
        _settings.SetSelectedSiteId(siteId);
        _ = RefreshAsync(showFlyout: true);
    }

    private async Task RefreshAsync(bool showFlyout)
    {
        if (!_settings.IsConfigured() || !_tokens.HasToken())
        {
            _latestError = "Konfigurera server och token.";
            UpdatePresentation();
            if (showFlyout)
            {
                _flyout.ShowError(_latestError);
            }

            return;
        }

        try
        {
            _sites = await _apiClient.GetSitesAsync();
            var siteId = _settings.GetSelectedSiteId();
            if (string.IsNullOrWhiteSpace(siteId))
            {
                var me = await _apiClient.GetMeAsync();
                siteId = me.DefaultSiteSlug ?? _sites.FirstOrDefault()?.Id;
            }

            _latestStatus = await _apiClient.GetStatusAsync(siteId);
            _latestError = null;
            UpdatePresentation();
            if (showFlyout)
            {
                _flyout.Bind(_latestStatus, _sites, siteId, null);
            }
        }
        catch (EmicApiException ex)
        {
            _latestError = ex.Message;
            UpdatePresentation();
            if (showFlyout)
            {
                _flyout.Bind(_latestStatus, _sites, _settings.GetSelectedSiteId(), ex.Message);
            }
        }
        catch (Exception ex)
        {
            _latestError = ex.Message;
            UpdatePresentation();
            if (showFlyout)
            {
                _flyout.ShowError(ex.Message);
            }
        }
    }

    private void UpdatePresentation()
    {
        var isError = !string.IsNullOrWhiteSpace(_latestError);
        var isStale = _latestStatus?.IsStale == true;

        _notifyIcon.Text = EnergyFormatter.BuildTrayTooltip(_latestStatus, _latestError);
        _notifyIcon.Icon = TrayIconFactory.Create(isStale: isStale, isError: isError);

        _chip.SetChipText(
            EnergyFormatter.BuildTaskbarChipText(_latestStatus, _latestError),
            isStale,
            isError);
        DockChip();
    }

    private static void Shutdown()
    {
        System.Windows.Application.Current.Shutdown();
    }

    public void Dispose()
    {
        SystemEvents.DisplaySettingsChanged -= _displaySettingsChangedHandler;
        _refreshTimer.Stop();
        _flyout.Close();
        _chip.Close();
        _notifyIcon.Visible = false;
        _notifyIcon.Dispose();
        _apiClient.Dispose();
    }
}
