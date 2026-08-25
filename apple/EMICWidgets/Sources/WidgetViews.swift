import EMICKit
import SwiftUI
import WidgetKit

struct EMICWidgetEntryView: View {
    @Environment(\.widgetFamily) private var family
    let entry: EMICEntry

    var body: some View {
        switch family {
        case .systemSmall:
            SmallWidgetView(entry: entry)
        case .systemMedium:
            MediumWidgetView(entry: entry)
        case .systemLarge:
            LargeWidgetView(entry: entry)
        default:
            MediumWidgetView(entry: entry)
        }
    }
}

struct SmallWidgetView: View {
    let entry: EMICEntry

    var body: some View {
        if let status = entry.status {
            VStack(alignment: .leading, spacing: 6) {
                Text(status.site.name.uppercased())
                    .font(.caption.bold())
                Label(EnergyFormatter.power(status.solar.powerKw), systemImage: "sun.max.fill")
                    .foregroundStyle(.orange)
                Label("\(EnergyFormatter.percent(status.battery.socPercent))  \(EnergyFormatter.power(status.battery.powerKw))", systemImage: "battery.75")
                    .foregroundStyle(.green)
                Label("\(StatusMapper.gridLabel(direction: status.grid.direction)) \(EnergyFormatter.power(status.grid.exportPowerKw ?? status.grid.importPowerKw))", systemImage: "bolt.horizontal.fill")
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .accessibilityLabel(accessibilityText(for: status))
        } else {
            Text(NSLocalizedString("offlineHint", comment: ""))
        }
    }

    private func accessibilityText(for status: WidgetStatusResponse) -> String {
        "\(status.site.name). Sol \(EnergyFormatter.power(status.solar.powerKw)). \(StatusMapper.batteryAccessibility(status.battery))"
    }
}

struct MediumWidgetView: View {
    let entry: EMICEntry

    var body: some View {
        if let status = entry.status {
            VStack(alignment: .leading, spacing: 8) {
                Text(status.site.name).font(.headline)
                row("sun.max.fill", NSLocalizedString("solar", comment: ""), EnergyFormatter.power(status.solar.powerKw), .orange)
                row("house.fill", NSLocalizedString("house", comment: ""), EnergyFormatter.power(status.house.powerKw), .primary)
                row("battery.75", NSLocalizedString("battery", comment: ""), "\(EnergyFormatter.percent(status.battery.socPercent)) / \(EnergyFormatter.power(status.battery.powerKw))", .green)
                row("bolt.horizontal.fill", NSLocalizedString("grid", comment: ""), "\(StatusMapper.gridLabel(direction: status.grid.direction)) \(EnergyFormatter.power(status.grid.exportPowerKw ?? status.grid.importPowerKw))", .blue)
                row("bolt.car.fill", NSLocalizedString("ev", comment: ""), status.ev.stateText ?? status.ev.state, .primary)
                row("banknote", NSLocalizedString("savedToday", comment: ""), EnergyFormatter.sek(status.economy.savedTodaySek, integer: true), .primary)
                Text(status.emic.decisionText)
                    .font(.footnote)
                    .foregroundStyle(.secondary)
                Text(EnergyFormatter.freshness(updatedAt: status.updatedAt, dataAgeSeconds: status.dataAgeSeconds, isStale: status.isStale || entry.isOffline))
                    .font(.caption2)
                    .foregroundStyle(entry.isOffline || status.isStale ? .orange : .secondary)
            }
        } else {
            Text(NSLocalizedString("offlineHint", comment: ""))
        }
    }

    private func row(_ icon: String, _ title: String, _ value: String, _ color: Color) -> some View {
        HStack {
            Label(title, systemImage: icon).labelStyle(.titleAndIcon).foregroundStyle(color)
            Spacer()
            Text(value).fontWeight(.semibold)
        }
        .font(.caption)
    }
}

struct LargeWidgetView: View {
    let entry: EMICEntry

    var body: some View {
        if let summary = entry.summary {
            VStack(alignment: .leading, spacing: 12) {
                ForEach(summary.sites, id: \.site.id) { siteStatus in
                    siteBlock(siteStatus)
                }
                Divider()
                Text("TOTALT IDAG")
                    .font(.caption.bold())
                Text("☀️ \(EnergyFormatter.power(summary.totals.solarPowerKw))")
                Text("💰 \(EnergyFormatter.sek(summary.totals.savedTodaySek, integer: true)) sparat")
            }
        } else if let status = entry.status {
            siteBlock(status)
            EnergyFlowView(status: status)
        } else {
            Text(NSLocalizedString("offlineHint", comment: ""))
        }
    }

    @ViewBuilder
    private func siteBlock(_ status: WidgetStatusResponse) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(status.site.name.uppercased()).font(.headline)
            Text("☀️ \(EnergyFormatter.power(status.solar.powerKw))")
            Text("🏠 \(EnergyFormatter.power(status.house.powerKw))")
            Text("🔋 \(EnergyFormatter.percent(status.battery.socPercent))")
            Text("🌐 \(StatusMapper.gridLabel(direction: status.grid.direction)) \(EnergyFormatter.power(status.grid.exportPowerKw ?? status.grid.importPowerKw))")
        }
    }
}

struct EnergyFlowView: View {
    let status: WidgetStatusResponse

    var body: some View {
        VStack(spacing: 4) {
            Image(systemName: "sun.max.fill")
            Text(EnergyFormatter.power(status.solar.powerKw))
            Image(systemName: "arrow.down")
            Image(systemName: "house.fill")
            Text(EnergyFormatter.power(status.house.powerKw))
            HStack {
                VStack {
                    Image(systemName: "battery.75")
                    Text(EnergyFormatter.power(status.battery.powerKw))
                }
                Spacer()
                VStack {
                    Image(systemName: "bolt.horizontal.fill")
                    Text(EnergyFormatter.power(status.grid.powerKw.map(abs)))
                }
            }
        }
        .font(.caption2)
        .padding(.top, 8)
    }
}

#if DEBUG
#Preview(as: .systemSmall) {
    EMICWidgets()
} timeline: {
    EMICEntry(date: .now, status: PreviewData.akarpStatus, summary: nil, isOffline: false, siteName: "Åkarp")
}

#Preview(as: .systemMedium) {
    EMICWidgets()
} timeline: {
    EMICEntry(date: .now, status: PreviewData.akarpStatus, summary: nil, isOffline: false, siteName: "Åkarp")
}
#endif
