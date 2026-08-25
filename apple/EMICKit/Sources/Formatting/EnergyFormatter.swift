import Foundation

public enum EnergyFormatter {
    public static var locale: Locale = Locale(identifier: "sv_SE")

    public static func power(_ kilowatts: Double?) -> String {
        guard let kilowatts else { return "—" }
        if abs(kilowatts) < 1 {
            let watts = Int((kilowatts * 1000).rounded())
            return "\(watts) W"
        }
        return String(format: "%.1f kW", locale: locale, kilowatts)
    }

    public static func energyKwh(_ value: Double?) -> String {
        guard let value else { return "—" }
        return String(format: "%.1f kWh", locale: locale, value)
    }

    public static func percent(_ value: Double?) -> String {
        guard let value else { return "—" }
        return String(format: "%.0f %%", locale: locale, value)
    }

    public static func sek(_ value: Double?, integer: Bool = false) -> String {
        guard let value else { return "—" }
        if integer {
            return String(format: "%.0f kr", locale: locale, value)
        }
        return String(format: "%.0f kr", locale: locale, value.rounded())
    }

    public static func freshness(updatedAt: Date?, dataAgeSeconds: Int?, isStale: Bool) -> String {
        if isStale, let dataAgeSeconds {
            let minutes = max(1, dataAgeSeconds / 60)
            return String(format: NSLocalizedString("freshness.stale", comment: ""), minutes)
        }
        if let updatedAt {
            let formatter = DateFormatter()
            formatter.locale = locale
            formatter.timeStyle = .short
            formatter.dateStyle = .none
            return String(format: NSLocalizedString("freshness.updatedAt", comment: ""), formatter.string(from: updatedAt))
        }
        return NSLocalizedString("freshness.unknown", comment: "")
    }
}

public enum StatusMapper {
    public static func gridLabel(direction: String?) -> String {
        switch direction {
        case "import": return NSLocalizedString("grid.import", comment: "")
        case "export": return NSLocalizedString("grid.export", comment: "")
        default: return "—"
        }
    }

    public static func batteryAccessibility(_ battery: WidgetBatterySection) -> String {
        let soc = battery.socPercent.map { Int($0.rounded()) } ?? 0
        let power = EnergyFormatter.power(battery.powerKw)
        return String(format: NSLocalizedString("a11y.battery", comment: ""), soc, power)
    }
}
