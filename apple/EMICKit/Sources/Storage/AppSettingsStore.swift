import Foundation

public enum AppSettingsStore {
    private static let appGroup = "group.net.inacloud.emic"
    private static let serverURLKey = "server-base-url"

    public static func serverURL() -> URL? {
        guard let raw = UserDefaults(suiteName: appGroup)?.string(forKey: serverURLKey) else {
            return nil
        }
        return URL(string: raw)
    }

    public static func setServerURL(_ url: URL) {
        UserDefaults(suiteName: appGroup)?.set(url.absoluteString, forKey: serverURLKey)
    }
}
