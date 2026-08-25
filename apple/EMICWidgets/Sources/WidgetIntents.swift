import AppIntents
import EMICKit

struct SiteEntity: AppEntity, Identifiable {
    static var typeDisplayRepresentation = TypeDisplayRepresentation(name: "Plats")
    static var defaultQuery = SiteEntityQuery()

    var id: String
    var name: String

    var displayRepresentation: DisplayRepresentation {
        DisplayRepresentation(title: "\(name)")
    }
}

struct SiteEntityQuery: EntityQuery {
    func entities(for identifiers: [SiteEntity.ID]) async throws -> [SiteEntity] {
        let sites = (try? await WidgetDataLoader.loadSites()) ?? defaultSites()
        return sites.filter { identifiers.contains($0.id) }
    }

    func suggestedEntities() async throws -> [SiteEntity] {
        if let sites = try? await WidgetDataLoader.loadSites(), !sites.isEmpty {
            return sites.map { SiteEntity(id: $0.id, name: $0.name) }
        }
        return defaultSites()
    }

    private func defaultSites() -> [SiteEntity] {
        [
            SiteEntity(id: SiteSelection.all.rawValue, name: SiteSelection.all.title),
            SiteEntity(id: SiteSelection.akarp.rawValue, name: SiteSelection.akarp.title),
            SiteEntity(id: SiteSelection.denmark.rawValue, name: SiteSelection.denmark.title),
        ]
    }
}

struct WidgetSiteSelectionIntent: WidgetConfigurationIntent {
    static var title: LocalizedStringResource = "Plats"
    static var description = IntentDescription("Välj vilken anläggning widgeten ska visa.")

    @Parameter(title: "Plats")
    var site: SiteEntity?
}

enum WidgetDataLoader {
    static func loadSites() async throws -> [WidgetSiteListItem] {
        guard let url = AppSettingsStore.serverURL(), KeychainStore.loadToken() != nil else {
            throw EMICError.noConnection
        }
        let client = EMICApiClient(
            configuration: EMICConfiguration(baseURL: url),
            tokenProvider: { KeychainStore.loadToken() }
        )
        return try await client.getSites()
    }

    static func loadStatus(for siteId: String?) async throws -> WidgetStatusResponse {
        guard let url = AppSettingsStore.serverURL(), KeychainStore.loadToken() != nil else {
            throw EMICError.noConnection
        }
        let client = EMICApiClient(
            configuration: EMICConfiguration(baseURL: url),
            tokenProvider: { KeychainStore.loadToken() }
        )
        if siteId == SiteSelection.all.rawValue {
            let summary = try await client.getSummary()
            if let first = summary.sites.first {
                return first
            }
            throw EMICError.noData
        }
        return try await client.getWidgetStatus(siteId: siteId)
    }

    static func loadSummary() async throws -> WidgetSummaryResponse {
        guard let url = AppSettingsStore.serverURL(), KeychainStore.loadToken() != nil else {
            throw EMICError.noConnection
        }
        let client = EMICApiClient(
            configuration: EMICConfiguration(baseURL: url),
            tokenProvider: { KeychainStore.loadToken() }
        )
        return try await client.getSummary()
    }
}
