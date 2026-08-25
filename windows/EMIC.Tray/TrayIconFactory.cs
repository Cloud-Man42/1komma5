using System.Drawing;
using System.Drawing.Drawing2D;

namespace EMIC.Tray;

internal static class TrayIconFactory
{
    public static Icon Create(bool isStale, bool isError)
    {
        using var bitmap = new Bitmap(16, 16);
        using var graphics = Graphics.FromImage(bitmap);
        graphics.SmoothingMode = SmoothingMode.AntiAlias;
        graphics.Clear(Color.Transparent);

        var fill = isError ? Color.FromArgb(220, 53, 69) :
            isStale ? Color.FromArgb(255, 193, 7) :
            Color.FromArgb(25, 135, 84);
        using var brush = new SolidBrush(fill);
        graphics.FillEllipse(brush, 1, 1, 14, 14);
        using var pen = new Pen(Color.White, 1.5f);
        graphics.DrawLine(pen, 8, 4, 8, 9);
        graphics.DrawLine(pen, 8, 11, 8, 12);

        return Icon.FromHandle(bitmap.GetHicon());
    }
}
