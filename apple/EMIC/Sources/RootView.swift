import EMICKit
import SwiftUI

struct RootView: View {
    @EnvironmentObject private var appModel: AppModel

    var body: some View {
        NavigationStack {
            if appModel.isConfigured {
                DashboardView()
            } else {
                OnboardingView()
            }
        }
    }
}

struct OnboardingView: View {
    @EnvironmentObject private var appModel: AppModel

    var body: some View {
        Form {
            Section("EMIC") {
                TextField("Server-URL", text: $appModel.serverURLString)
                    .textInputAutocapitalization(.never)
                    .keyboardType(.URL)
                SecureField("Device-token", text: $appModel.token)
            }
            Button("Spara") {
                appModel.saveCredentials()
            }
        }
        .navigationTitle("EMIC")
    }
}

struct DashboardView: View {
    @EnvironmentObject private var appModel: AppModel

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                Picker("Plats", selection: $appModel.selectedSite) {
                    ForEach(SiteSelection.allCases, id: \.self) { site in
                        Text(site.title).tag(site)
                    }
                }
                .pickerStyle(.segmented)

                if let status = appModel.status {
                    StatusCardView(status: status)
                } else if appModel.isLoading {
                    ProgressView()
                } else {
                    Text(NSLocalizedString("error.noData", comment: ""))
                        .foregroundStyle(.secondary)
                }

                if let error = appModel.errorMessage {
                    Text(error)
                        .foregroundStyle(.orange)
                }
            }
            .padding()
        }
        .navigationTitle("EMIC")
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button("Uppdatera") {
                    Task { await appModel.refresh() }
                }
            }
        }
        .task {
            await appModel.refresh()
        }
        .onChange(of: appModel.selectedSite) { _, _ in
            Task { await appModel.refresh() }
        }
    }
}

struct StatusCardView: View {
    let status: WidgetStatusResponse

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(status.site.name)
                .font(.title2.bold())

            MetricRow(title: NSLocalizedString("solar", comment: ""), value: EnergyFormatter.power(status.solar.powerKw))
            MetricRow(title: NSLocalizedString("house", comment: ""), value: EnergyFormatter.power(status.house.powerKw))
            MetricRow(
                title: NSLocalizedString("battery", comment: ""),
                value: "\(EnergyFormatter.percent(status.battery.socPercent)) / \(EnergyFormatter.power(status.battery.powerKw))"
            )
            MetricRow(
                title: NSLocalizedString("grid", comment: ""),
                value: "\(StatusMapper.gridLabel(direction: status.grid.direction)) \(EnergyFormatter.power(status.grid.powerKw.map(abs)))"
            )
            MetricRow(title: NSLocalizedString("ev", comment: ""), value: status.ev.stateText ?? status.ev.state)
            MetricRow(title: NSLocalizedString("savedToday", comment: ""), value: EnergyFormatter.sek(status.economy.savedTodaySek, integer: true))

            Text(EnergyFormatter.freshness(updatedAt: status.updatedAt, dataAgeSeconds: status.dataAgeSeconds, isStale: status.isStale))
                .font(.footnote)
                .foregroundStyle(status.isStale ? .orange : .secondary)

            VStack(alignment: .leading, spacing: 4) {
                Text(NSLocalizedString("emicStatus", comment: ""))
                    .font(.headline)
                Text(status.emic.decisionText)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding()
        .background(.thinMaterial, in: RoundedRectangle(cornerRadius: 16))
        .accessibilityElement(children: .combine)
    }
}

struct MetricRow: View {
    let title: String
    let value: String

    var body: some View {
        HStack {
            Text(title)
            Spacer()
            Text(value)
                .fontWeight(.semibold)
        }
    }
}

#if DEBUG
#Preview {
    RootView()
        .environmentObject({
            let model = AppModel()
            model.isConfigured = true
            model.status = PreviewData.akarpStatus
            return model
        }())
}
#endif
