using System.Runtime.InteropServices;
using System.Windows;

namespace EMIC.Tray;

internal static class TaskbarHelper
{
    private const int AbmGetTaskbarPos = 0x00000005;

    [StructLayout(LayoutKind.Sequential)]
    private struct RectNative
    {
        public int Left;
        public int Top;
        public int Right;
        public int Bottom;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct AppBarData
    {
        public int cbSize;
        public IntPtr hWnd;
        public int uCallbackMessage;
        public int uEdge;
        public RectNative rc;
        public int lParam;
    }

    [DllImport("shell32.dll")]
    private static extern uint SHAppBarMessage(int dwMessage, ref AppBarData data);

    public static Rect GetTaskbarBounds()
    {
        var data = new AppBarData { cbSize = Marshal.SizeOf<AppBarData>() };
        _ = SHAppBarMessage(AbmGetTaskbarPos, ref data);
        return new Rect(
            data.rc.Left,
            data.rc.Top,
            data.rc.Right - data.rc.Left,
            data.rc.Bottom - data.rc.Top);
    }

    public static bool IsTaskbarBottom()
    {
        var taskbar = GetTaskbarBounds();
        var screen = SystemParameters.WorkArea;
        return taskbar.Top >= screen.Bottom - 1;
    }
}
