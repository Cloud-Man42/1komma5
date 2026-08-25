import Foundation

public struct EMICConfiguration: Sendable {
    public var baseURL: URL
    public var requestTimeout: TimeInterval
    public var retryCount: Int

    public init(
        baseURL: URL,
        requestTimeout: TimeInterval = 15,
        retryCount: Int = 2
    ) {
        self.baseURL = baseURL
        self.requestTimeout = requestTimeout
        self.retryCount = retryCount
    }
}

public protocol EMICApiClientProtocol: Sendable {
    func getSites() async throws -> [WidgetSiteListItem]
    func getWidgetStatus(siteId: String?) async throws -> WidgetStatusResponse
    func getSummary() async throws -> WidgetSummaryResponse
    func getMe() async throws -> WidgetMeResponse
}

public final class EMICApiClient: EMICApiClientProtocol, @unchecked Sendable {
    private let configuration: EMICConfiguration
    private let session: URLSession
    private let tokenProvider: @Sendable () -> String?
    private let decoder: JSONDecoder

    public init(
        configuration: EMICConfiguration,
        tokenProvider: @escaping @Sendable () -> String?,
        session: URLSession = .shared
    ) {
        self.configuration = configuration
        self.tokenProvider = tokenProvider
        self.session = session
        self.decoder = JSONDecoder()
        self.decoder.dateDecodingStrategy = .iso8601
    }

    public func getSites() async throws -> [WidgetSiteListItem] {
        let response: WidgetSitesResponse = try await request(path: "/api/v1/widget/sites")
        return response.sites
    }

    public func getWidgetStatus(siteId: String?) async throws -> WidgetStatusResponse {
        if let siteId, !siteId.isEmpty {
            return try await request(path: "/api/v1/widget/status/\(siteId)")
        }
        return try await request(path: "/api/v1/widget/status")
    }

    public func getSummary() async throws -> WidgetSummaryResponse {
        try await request(path: "/api/v1/widget/summary")
    }

    public func getMe() async throws -> WidgetMeResponse {
        try await request(path: "/api/v1/widget/me")
    }

    private func request<T: Decodable>(path: String) async throws -> T {
        guard let token = tokenProvider(), !token.isEmpty else {
            throw EMICError.unauthorized
        }

        var lastError: Error = EMICError.noConnection
        for attempt in 0...configuration.retryCount {
            do {
                return try await performRequest(path: path, token: token)
            } catch {
                lastError = error
                if attempt < configuration.retryCount, shouldRetry(error) {
                    try await Task.sleep(nanoseconds: UInt64(250_000_000 * (attempt + 1)))
                    continue
                }
                throw error
            }
        }
        throw lastError
    }

    private func performRequest<T: Decodable>(path: String, token: String) async throws -> T {
        let trimmedBase = configuration.baseURL.absoluteString.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        guard let url = URL(string: trimmedBase + path) else {
            throw EMICError.invalidResponse
        }
        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        request.timeoutInterval = configuration.requestTimeout
        request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        request.setValue("application/json", forHTTPHeaderField: "Accept")

        let (data, response): (Data, URLResponse)
        do {
            (data, response) = try await session.data(for: request)
        } catch let error as URLError where error.code == .timedOut {
            throw EMICError.timeout
        } catch {
            throw EMICError.noConnection
        }

        guard let http = response as? HTTPURLResponse else {
            throw EMICError.invalidResponse
        }

        switch http.statusCode {
        case 200...299:
            break
        case 401:
            throw EMICError.unauthorized
        case 403:
            throw EMICError.forbidden
        case 429:
            throw EMICError.rateLimited
        case 500...599:
            throw EMICError.serverError
        default:
            throw EMICError.invalidResponse
        }

        do {
            return try decoder.decode(T.self, from: data)
        } catch {
            throw EMICError.decodeError
        }
    }

    private func shouldRetry(_ error: Error) -> Bool {
        guard let emicError = error as? EMICError else { return false }
        switch emicError {
        case .timeout, .noConnection, .serverError, .rateLimited:
            return true
        default:
            return false
        }
    }
}
