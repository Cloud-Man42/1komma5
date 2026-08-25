using System.Windows;
using System.Windows.Input;
using System.Windows.Media;

namespace EMIC.Tray.Views;

public partial class TaskbarChipWindow : Window
{
    private bool _dragging;
    private System.Windows.Point _dragStart;
    private double _dragStartLeft;

    public event EventHandler? ChipClicked;
    public event EventHandler? OpenSettingsRequested;
    public event EventHandler? RefreshRequested;
    public event EventHandler? ExitRequested;
    public event EventHandler<double>? ChipOffsetChanged;

    public TaskbarChipWindow()
    {
        InitializeComponent();
    }

    public void SetChipText(string text, bool isStale, bool isError)
    {
        ChipText.Text = text;
        ChipBorder.Background = new SolidColorBrush(isError
            ? System.Windows.Media.Color.FromArgb(0xCC, 0x8B, 0x1A, 0x24)
            : isStale
                ? System.Windows.Media.Color.FromArgb(0xCC, 0x66, 0x5C, 0x00)
                : System.Windows.Media.Color.FromArgb(0xCC, 0x2B, 0x2B, 0x2B));
    }

    public void DockToTaskbar(double offsetX)
    {
        UpdateLayout();
        var taskbar = TaskbarHelper.GetTaskbarBounds();
        var workArea = SystemParameters.WorkArea;
        var width = ActualWidth > 0 ? ActualWidth : Width;
        var height = ActualWidth > 0 ? ActualHeight : Height;

        var maxLeft = workArea.Right - width - 8;
        var left = Math.Clamp(offsetX, workArea.Left + 4, maxLeft);

        Left = left;
        if (TaskbarHelper.IsTaskbarBottom())
        {
            Top = taskbar.Top + ((taskbar.Height - height) / 2);
        }
        else
        {
            Top = workArea.Bottom - height - 4;
        }
    }

    private void Window_MouseLeftButtonDown(object sender, MouseButtonEventArgs e)
    {
        if (e.ClickCount >= 2)
        {
            ChipClicked?.Invoke(this, EventArgs.Empty);
            return;
        }

        _dragging = true;
        _dragStart = PointToScreen(e.GetPosition(this));
        _dragStartLeft = Left;
        CaptureMouse();
    }

    private void Window_MouseMove(object sender, System.Windows.Input.MouseEventArgs e)
    {
        if (!_dragging)
        {
            return;
        }

        var current = PointToScreen(e.GetPosition(this));
        var delta = current.X - _dragStart.X;
        DockToTaskbar(_dragStartLeft + delta);
    }

    private void Window_MouseLeftButtonUp(object sender, MouseButtonEventArgs e)
    {
        if (!_dragging)
        {
            return;
        }

        _dragging = false;
        ReleaseMouseCapture();
        ChipOffsetChanged?.Invoke(this, Left);
        if (Math.Abs(PointToScreen(e.GetPosition(this)).X - _dragStart.X) < 4)
        {
            ChipClicked?.Invoke(this, EventArgs.Empty);
        }
    }

    protected override void OnMouseRightButtonUp(MouseButtonEventArgs e)
    {
        base.OnMouseRightButtonUp(e);
        var menu = new System.Windows.Controls.ContextMenu();
        menu.Items.Add(CreateItem("Visa detaljer", (_, _) => ChipClicked?.Invoke(this, EventArgs.Empty)));
        menu.Items.Add(CreateItem("Uppdatera", (_, _) => RefreshRequested?.Invoke(this, EventArgs.Empty)));
        menu.Items.Add(CreateItem("Inställningar…", (_, _) => OpenSettingsRequested?.Invoke(this, EventArgs.Empty)));
        menu.Items.Add(new System.Windows.Controls.Separator());
        menu.Items.Add(CreateItem("Avsluta", (_, _) => ExitRequested?.Invoke(this, EventArgs.Empty)));
        menu.IsOpen = true;
    }

    private static System.Windows.Controls.MenuItem CreateItem(string header, RoutedEventHandler click)
    {
        var item = new System.Windows.Controls.MenuItem { Header = header };
        item.Click += click;
        return item;
    }
}
