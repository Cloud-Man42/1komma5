import Foundation

public struct CachedSnapshot: Codable, Sendable {
    public let status: WidgetStatusResponse
    public let cachedAt: Date
}

public enum SnapshotStore {
    private static let appGroup = "group.net.inacloud.emic"
    private static let fileName = "latest-widget-status.json"
    private static let sitePreferenceKey = "preferred-site-slug"

    private static var containerURL: URL? {
        FileManager.default.containerURL(forSecurityApplicationGroupIdentifier: appGroup)
    }

    public static func save(_ status: WidgetStatusResponse) throws {
        guard let url = fileURL else { return }
        let payload = CachedSnapshot(status: status, cachedAt: Date())
        let data = try JSONEncoder().encode(payload)
        try data.write(to: url, options: .atomic)
    }

    public static func load() -> CachedSnapshot? {
        guard let url = fileURL, let data = try? Data(contentsOf: url) else { return nil }
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        return try? decoder.decode(CachedSnapshot.self, from: data)
    }

    public static func preferredSiteSlug() -> String? {
        UserDefaults(suiteName: appGroup)?.string(forKey: sitePreferenceKey)
    }

    public static func setPreferredSiteSlug(_ slug: String?) {
        UserDefaults(suiteName: appGroup)?.set(slug, forKey: sitePreferenceKey)
    }

    private static var fileURL: URL? {
        containerURL?.appendingPathComponent(fileName)
    }
}
