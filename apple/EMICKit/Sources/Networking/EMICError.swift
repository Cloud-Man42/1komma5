import Foundation

public enum EMICError: Error, Equatable, Sendable {
    case noConnection
    case unauthorized
    case forbidden
    case serverError
    case invalidResponse
    case decodeError
    case timeout
    case staleData
    case noData
    case rateLimited

    public var userMessageKey: String {
        switch self {
        case .noConnection: return "error.noConnection"
        case .unauthorized: return "error.unauthorized"
        case .forbidden: return "error.forbidden"
        case .serverError: return "error.serverError"
        case .invalidResponse: return "error.invalidResponse"
        case .decodeError: return "error.decodeError"
        case .timeout: return "error.timeout"
        case .staleData: return "error.staleData"
        case .noData: return "error.noData"
        case .rateLimited: return "error.rateLimited"
        }
    }
}
