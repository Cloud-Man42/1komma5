using System.Windows;
using System.Windows.Controls;
using EMIC.Core.Storage;

namespace EMIC.Tray.Views;

public partial class SetupWindow : Window
{
    private readonly AppSettingsStore _settings;
    private readonly TokenStore _tokens;

    public SetupWindow(AppSettingsStore settings, TokenStore tokens)
    {
        _settings = settings;
        _tokens = tokens;
        InitializeComponent();
        ServerUrlBox.Text = _settings.GetServerUrl() ?? "http://localhost:8000";
        TokenBox.Password = _tokens.LoadToken() ?? string.Empty;
        SiteBox.Text = _settings.GetSelectedSiteId() ?? "akarp";
        SelectDisplayMode(_settings.GetDisplayMode());
    }

    public bool Saved { get; private set; }

    private void SelectDisplayMode(WidgetDisplayMode mode)
    {
        foreach (ComboBoxItem item in DisplayModeBox.Items)
        {
            if (item.Tag is string tag && tag == mode.ToString())
            {
                DisplayModeBox.SelectedItem = item;
                return;
            }
        }

        DisplayModeBox.SelectedIndex = 2;
    }

    private WidgetDisplayMode ReadDisplayMode()
    {
        if (DisplayModeBox.SelectedItem is ComboBoxItem item && item.Tag is string tag
            && Enum.TryParse<WidgetDisplayMode>(tag, out var mode))
        {
            return mode;
        }

        return WidgetDisplayMode.Taskbar;
    }

    private void SaveButton_Click(object sender, RoutedEventArgs e)
    {
        ErrorText.Visibility = Visibility.Collapsed;
        var serverUrl = ServerUrlBox.Text.Trim();
        var token = TokenBox.Password.Trim();
        if (string.IsNullOrWhiteSpace(serverUrl) || string.IsNullOrWhiteSpace(token))
        {
            ErrorText.Text = "Server-URL och device-token krävs.";
            ErrorText.Visibility = Visibility.Visible;
            return;
        }

        if (!token.StartsWith("emic_", StringComparison.Ordinal))
        {
            ErrorText.Text = "Token ska börja med emic_.";
            ErrorText.Visibility = Visibility.Visible;
            return;
        }

        _settings.Save(serverUrl, SiteBox.Text.Trim(), displayMode: ReadDisplayMode());
        _tokens.SaveToken(token);
        Saved = true;
        Close();
    }

    private void CancelButton_Click(object sender, RoutedEventArgs e) => Close();
}
