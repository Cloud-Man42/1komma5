import EMICKit
import XCTest

final class WidgetKitTests: XCTestCase {
    func testDecodesFixtureStatus() throws {
        let url = fixtureURL(named: "widget-status-akarp.json")
        let data = try Data(contentsOf: url)
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        let status = try decoder.decode(WidgetStatusResponse.self, from: data)
        XCTAssertEqual(status.site.id, "akarp")
        XCTAssertEqual(status.grid.direction, "export")
    }

    func testFormatterUsesWattsBelowOneKw() {
        XCTAssertEqual(EnergyFormatter.power(0.48), "480 W")
    }

    func testGridLabels() {
        XCTAssertEqual(StatusMapper.gridLabel(direction: "export"), NSLocalizedString("grid.export", comment: ""))
    }

    func testPreferredSiteRoundTrip() {
        SnapshotStore.setPreferredSiteSlug("akarp")
        XCTAssertEqual(SnapshotStore.preferredSiteSlug(), "akarp")
    }

    private func fixtureURL(named: String) -> URL {
        let root = URL(fileURLWithPath: #file).deletingLastPathComponent().deletingLastPathComponent()
        return root.appendingPathComponent("Fixtures/\(named)")
    }
}
