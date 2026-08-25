import SwiftUI
import WidgetKit

@main
struct EMICWidgets: Widget {
    let kind = "EMICWidgets"

    var body: some WidgetConfiguration {
        AppIntentConfiguration(
            kind: kind,
            intent: WidgetSiteSelectionIntent.self,
            provider: EMICProvider()
        ) { entry in
            EMICWidgetEntryView(entry: entry)
                .containerBackground(.fill.tertiary, for: .widget)
        }
        .configurationDisplayName("EMIC Status")
        .description("Visa aktuell energistatus från EMIC.")
        .supportedFamilies([.systemSmall, .systemMedium, .systemLarge])
    }
}
