import Foundation

#if DEBUG
public enum PreviewData {
    public static let akarpStatus = WidgetStatusResponse(
        apiVersion: "1.0",
        site: WidgetSiteRef(id: "akarp", name: "Åkarp"),
        solar: WidgetSolarSection(powerKw: 5.42, todayKwh: 21.6),
        house: WidgetHouseSection(powerKw: 1.61, todayKwh: 11.8),
        battery: WidgetBatterySection(socPercent: 74, powerKw: 2.34, state: "charging", stateText: "Laddar"),
        grid: WidgetGridSection(powerKw: -1.47, direction: "export", importPowerKw: 0, exportPowerKw: 1.47),
        ev: WidgetEvSection(state: "waiting", stateText: "Väntar", powerKw: 0, energyTodayKwh: nil),
        economy: WidgetEconomySection(savedTodaySek: 63, savedMonthSek: 1187, economicDataQuality: "measured"),
        smartCharging: WidgetSmartChargingSection(mode: "smart", state: "waiting_for_surplus", decisionText: "Väntar på solel"),
        emic: WidgetEmicSection(mode: "SMART_CHARGE", decisionText: "Laddar batteriet med solel"),
        systemStatus: "online",
        updatedAt: Date(),
        dataAgeSeconds: 9,
        isStale: false
    )

    public static let denmarkStatus = WidgetStatusResponse(
        apiVersion: "1.0",
        site: WidgetSiteRef(id: "summer-house-denmark", name: "Danmark"),
        solar: WidgetSolarSection(powerKw: 2.1, todayKwh: 12.4),
        house: WidgetHouseSection(powerKw: 0.82, todayKwh: 4.2),
        battery: WidgetBatterySection(socPercent: 91, powerKw: 0.1, state: "idle", stateText: "Vilar"),
        grid: WidgetGridSection(powerKw: -0.42, direction: "export", importPowerKw: 0, exportPowerKw: 0.42),
        ev: WidgetEvSection(state: "unavailable", stateText: "Ej tillgänglig", powerKw: nil, energyTodayKwh: nil),
        economy: WidgetEconomySection(savedTodaySek: 28, savedMonthSek: 420, economicDataQuality: "estimated"),
        smartCharging: nil,
        emic: WidgetEmicSection(mode: nil, decisionText: "Säljer solelöverskott"),
        systemStatus: "online",
        updatedAt: Date(),
        dataAgeSeconds: 20,
        isStale: false
    )
}
#endif
