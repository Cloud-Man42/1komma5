import Foundation

public struct WidgetSiteRef: Codable, Hashable, Sendable {
    public let id: String
    public let name: String
}

public struct WidgetSolarSection: Codable, Hashable, Sendable {
    public let powerKw: Double?
    public let todayKwh: Double?
}

public struct WidgetHouseSection: Codable, Hashable, Sendable {
    public let powerKw: Double?
    public let todayKwh: Double?
}

public struct WidgetBatterySection: Codable, Hashable, Sendable {
    public let socPercent: Double?
    public let powerKw: Double?
    public let state: String
    public let stateText: String?
}

public struct WidgetGridSection: Codable, Hashable, Sendable {
    public let powerKw: Double?
    public let direction: String?
    public let importPowerKw: Double?
    public let exportPowerKw: Double?
}

public struct WidgetEvSection: Codable, Hashable, Sendable {
    public let state: String
    public let stateText: String?
    public let powerKw: Double?
    public let energyTodayKwh: Double?
}

public struct WidgetEconomySection: Codable, Hashable, Sendable {
    public let savedTodaySek: Double?
    public let savedMonthSek: Double?
    public let economicDataQuality: String
}

public struct WidgetSmartChargingSection: Codable, Hashable, Sendable {
    public let mode: String?
    public let state: String?
    public let decisionText: String?
}

public struct WidgetEmicSection: Codable, Hashable, Sendable {
    public let mode: String?
    public let decisionText: String
}

public struct WidgetStatusResponse: Codable, Hashable, Sendable {
    public let apiVersion: String
    public let site: WidgetSiteRef
    public let solar: WidgetSolarSection
    public let house: WidgetHouseSection
    public let battery: WidgetBatterySection
    public let grid: WidgetGridSection
    public let ev: WidgetEvSection
    public let economy: WidgetEconomySection
    public let smartCharging: WidgetSmartChargingSection?
    public let emic: WidgetEmicSection
    public let systemStatus: String
    public let updatedAt: Date?
    public let dataAgeSeconds: Int?
    public let isStale: Bool
}

public struct WidgetSiteListItem: Codable, Hashable, Sendable {
    public let id: String
    public let name: String
    public let timezone: String
    public let systemStatus: String
}

public struct WidgetSitesResponse: Codable, Hashable, Sendable {
    public let apiVersion: String
    public let sites: [WidgetSiteListItem]
}

public struct WidgetSummaryTotals: Codable, Hashable, Sendable {
    public let solarPowerKw: Double?
    public let housePowerKw: Double?
    public let batteryStoredKwh: Double?
    public let savedTodaySek: Double?
}

public struct WidgetSummaryResponse: Codable, Hashable, Sendable {
    public let apiVersion: String
    public let sites: [WidgetStatusResponse]
    public let totals: WidgetSummaryTotals
    public let updatedAt: Date?
    public let dataAgeSeconds: Int?
    public let isStale: Bool
}

public struct WidgetMeResponse: Codable, Hashable, Sendable {
    public let apiVersion: String
    public let deviceId: Int
    public let ownerLabel: String
    public let deviceName: String
    public let deviceType: String
    public let defaultSiteSlug: String?
    public let scopes: [String]
    public let lastSeenAt: Date?
}

public enum SiteSelection: String, CaseIterable, Sendable {
    case akarp
    case denmark = "summer-house-denmark"
    case all

    public var title: String {
        switch self {
        case .akarp: return "Åkarp"
        case .denmark: return "Danmark"
        case .all: return "Alla"
        }
    }
}
