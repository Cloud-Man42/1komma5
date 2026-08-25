import EMICKit
import Foundation

@MainActor
final class AppModel: ObservableObject {
    @Published var serverURLString: String = AppSettingsStore.serverURL()?.absoluteString ?? ""
    @Published var token: String = KeychainStore.loadToken() ?? ""
    @Published var selectedSite: SiteSelection = .akarp
    @Published var status: WidgetStatusResponse?
    @Published var summary: WidgetSummaryResponse?
    @Published var errorMessage: String?
    @Published var isLoading = false
    @Published var isConfigured: Bool

    private var client: EMICApiClient?

    init() {
        isConfigured = AppSettingsStore.serverURL() != nil && KeychainStore.loadToken() != nil
        rebuildClient()
    }

    func rebuildClient() {
        guard let url = AppSettingsStore.serverURL() else {
            client = nil
            return
        }
        client = EMICApiClient(
            configuration: EMICConfiguration(baseURL: url),
            tokenProvider: { KeychainStore.loadToken() }
        )
    }

    func saveCredentials() {
        guard let url = URL(string: serverURLString.trimmingCharacters(in: .whitespacesAndNewlines)) else {
            errorMessage = NSLocalizedString("error.invalidResponse", comment: "")
            return
        }
        AppSettingsStore.setServerURL(url)
        try? KeychainStore.saveToken(token.trimmingCharacters(in: .whitespacesAndNewlines))
        isConfigured = true
        rebuildClient()
    }

    func refresh() async {
        guard let client else {
            errorMessage = NSLocalizedString("error.noConnection", comment: "")
            return
        }
        isLoading = true
        errorMessage = nil
        defer { isLoading = false }

        do {
            switch selectedSite {
            case .all:
                let loaded = try await client.getSummary()
                summary = loaded
                status = loaded.sites.first
                try? SnapshotStore.save(loaded.sites.first ?? loaded.sites[0])
            case .akarp, .denmark:
                let loaded = try await client.getWidgetStatus(siteId: selectedSite.rawValue)
                status = loaded
                summary = nil
                try? SnapshotStore.save(loaded)
            }
        } catch let error as EMICError {
            errorMessage = NSLocalizedString(error.userMessageKey, comment: "")
            if status == nil, let cached = SnapshotStore.load() {
                status = cached.status
            }
        } catch {
            errorMessage = NSLocalizedString("error.noConnection", comment: "")
            if status == nil, let cached = SnapshotStore.load() {
                status = cached.status
            }
        }
    }
}
