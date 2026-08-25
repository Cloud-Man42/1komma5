using System.Windows;
using System.Windows.Controls;
using EMIC.Core.Models;
using EMIC.Core.Services;

namespace EMIC.Tray.Views;

public partial class FlyoutWindow : Window
{
    public event EventHandler<string?>? SiteChanged;
    public event EventHandler? RefreshRequested;
    public event EventHandler? OpenSettingsRequested;

    public FlyoutWindow()
    {
        InitializeComponent();
    }

    public void Bind(
        WidgetStatusResponse? status,
        IReadOnlyList<WidgetSiteListItem> sites,
        string? selectedSiteId,
        string? errorMessage)
    {
        SiteSelector.ItemsSource = sites;
        SiteSelector.DisplayMemberPath = nameof(WidgetSiteListItem.Name);
        SiteSelector.SelectedValuePath = nameof(WidgetSiteListItem.Id);
        SiteSelector.SelectionChanged -= OnSiteSelectionChanged;
        SiteSelector.SelectedValue = selectedSiteId ?? status?.Site.Id;
        SiteSelector.SelectionChanged += OnSiteSelectionChanged;

        if (!string.IsNullOrWhiteSpace(errorMessage))
        {
            ErrorText.Text = errorMessage;
            ErrorText.Visibility = Visibility.Visible;
        }
        else
        {
            ErrorText.Visibility = Visibility.Collapsed;
        }

        if (status == null)
        {
            SiteTitle.Text = "EMIC";
            DecisionText.Text = errorMessage ?? "Ingen data";
            SolarValue.Text = HouseValue.Text = BatteryValue.Text = GridValue.Text = EvValue.Text = "—";
            MetaText.Text = string.Empty;
            StaleBadge.Visibility = Visibility.Collapsed;
            return;
        }

        SiteTitle.Text = status.Site.Name;
        DecisionText.Text = status.Emic.DecisionText;
        SolarValue.Text = EnergyFormatter.FormatPowerKw(status.Solar.PowerKw);
        HouseValue.Text = EnergyFormatter.FormatPowerKw(status.House.PowerKw);
        BatteryValue.Text = $"{EnergyFormatter.FormatSocPercent(status.Battery.SocPercent)} · {status.Battery.StateText ?? status.Battery.State}";
        GridValue.Text = $"{EnergyFormatter.GridLabel(status.Grid)} · {EnergyFormatter.FormatPowerKw(status.Grid.PowerKw is null ? null : Math.Abs(status.Grid.PowerKw.Value))}";
        EvValue.Text = status.Ev.StateText ?? status.Ev.State;
        MetaText.Text = EnergyFormatter.FormatAgeSeconds(status.DataAgeSeconds);
        StaleBadge.Visibility = status.IsStale ? Visibility.Visible : Visibility.Collapsed;
    }

    public void ShowError(string message)
    {
        ErrorText.Text = message;
        ErrorText.Visibility = Visibility.Visible;
    }

    private void OnSiteSelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (SiteSelector.SelectedValue is string siteId)
        {
            SiteChanged?.Invoke(this, siteId);
        }
    }

    private void RefreshButton_Click(object sender, RoutedEventArgs e) => RefreshRequested?.Invoke(this, EventArgs.Empty);

    private void SettingsButton_Click(object sender, RoutedEventArgs e) => OpenSettingsRequested?.Invoke(this, EventArgs.Empty);
}
