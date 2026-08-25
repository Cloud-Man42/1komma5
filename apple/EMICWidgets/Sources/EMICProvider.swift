import EMICKit
import WidgetKit

struct EMICEntry: TimelineEntry {
    let date: Date
    let status: WidgetStatusResponse?
    let summary: WidgetSummaryResponse?
    let isOffline: Bool
    let siteName: String
}

struct EMICProvider: AppIntentTimelineProvider {
    func placeholder(in context: Context) -> EMICEntry {
        EMICEntry(date: .now, status: nil, summary: nil, isOffline: false, siteName: "EMIC")
    }

    func snapshot(for configuration: WidgetSiteSelectionIntent, in context: Context) async -> EMICEntry {
        await loadEntry(for: configuration, isPreview: true)
    }

    func timeline(for configuration: WidgetSiteSelectionIntent, in context: Context) async -> Timeline<EMICEntry> {
        let entry = await loadEntry(for: configuration, isPreview: false)
        let nextUpdate = Calendar.current.date(byAdding: .minute, value: 15, to: .now) ?? .now.addingTimeInterval(900)
        return Timeline(entries: [entry], policy: .after(nextUpdate))
    }

    private func loadEntry(for configuration: WidgetSiteSelectionIntent, isPreview: Bool) async -> EMICEntry {
        #if DEBUG
        if isPreview {
            return EMICEntry(date: .now, status: PreviewData.akarpStatus, summary: nil, isOffline: false, siteName: "Åkarp")
        }
        #endif

        let siteId = configuration.site?.id
        let siteName = configuration.site?.name ?? "EMIC"

        do {
            if siteId == SiteSelection.all.rawValue {
                let summary = try await WidgetDataLoader.loadSummary()
                try? SnapshotStore.save(summary.sites.first ?? summary.sites[0])
                return EMICEntry(date: .now, status: summary.sites.first, summary: summary, isOffline: false, siteName: SiteSelection.all.title)
            }
            let status = try await WidgetDataLoader.loadStatus(for: siteId)
            try? SnapshotStore.save(status)
            return EMICEntry(date: .now, status: status, summary: nil, isOffline: false, siteName: status.site.name)
        } catch {
            if let cached = SnapshotStore.load() {
                return EMICEntry(date: .now, status: cached.status, summary: nil, isOffline: true, siteName: cached.status.site.name)
            }
            return EMICEntry(date: .now, status: nil, summary: nil, isOffline: true, siteName: siteName)
        }
    }
}
