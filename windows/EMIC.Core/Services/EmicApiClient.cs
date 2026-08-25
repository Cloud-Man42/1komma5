using System.Net;
using System.Net.Http.Headers;
using System.Text.Json;
using EMIC.Core.Models;
using EMIC.Core.Storage;

namespace EMIC.Core.Services;

public sealed class EmicApiClient : IDisposable
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNameCaseInsensitive = true,
    };

    private readonly HttpClient _httpClient;
    private readonly AppSettingsStore _settings;
    private readonly TokenStore _tokens;

    public EmicApiClient(AppSettingsStore settings, TokenStore tokens, HttpClient? httpClient = null)
    {
        _settings = settings;
        _tokens = tokens;
        _httpClient = httpClient ?? new HttpClient { Timeout = TimeSpan.FromSeconds(15) };
    }

    public async Task<IReadOnlyList<WidgetSiteListItem>> GetSitesAsync(CancellationToken cancellationToken = default)
    {
        var response = await GetAsync<WidgetSitesResponse>("/api/v1/widget/sites", cancellationToken);
        return response.Sites;
    }

    public Task<WidgetStatusResponse> GetStatusAsync(string? siteId = null, CancellationToken cancellationToken = default)
    {
        var path = string.IsNullOrWhiteSpace(siteId)
            ? "/api/v1/widget/status"
            : $"/api/v1/widget/status/{Uri.EscapeDataString(siteId)}";
        return GetAsync<WidgetStatusResponse>(path, cancellationToken);
    }

    public Task<WidgetSummaryResponse> GetSummaryAsync(CancellationToken cancellationToken = default)
        => GetAsync<WidgetSummaryResponse>("/api/v1/widget/summary", cancellationToken);

    public Task<WidgetMeResponse> GetMeAsync(CancellationToken cancellationToken = default)
        => GetAsync<WidgetMeResponse>("/api/v1/widget/me", cancellationToken);

    private async Task<T> GetAsync<T>(string path, CancellationToken cancellationToken)
    {
        var baseUrl = _settings.GetServerUrl();
        var token = _tokens.LoadToken();
        if (string.IsNullOrWhiteSpace(baseUrl))
        {
            throw new EmicApiException(EmicApiErrorCode.NotConfigured, "Server-URL saknas.");
        }

        if (string.IsNullOrWhiteSpace(token))
        {
            throw new EmicApiException(EmicApiErrorCode.Unauthorized, "Device-token saknas.");
        }

        var trimmed = baseUrl.TrimEnd('/');
        using var request = new HttpRequestMessage(HttpMethod.Get, trimmed + path);
        request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token);
        request.Headers.Accept.Add(new MediaTypeWithQualityHeaderValue("application/json"));

        HttpResponseMessage response;
        try
        {
            response = await _httpClient.SendAsync(request, cancellationToken);
        }
        catch (TaskCanceledException) when (!cancellationToken.IsCancellationRequested)
        {
            throw new EmicApiException(EmicApiErrorCode.Timeout, "Anslutningen tog för lång tid.");
        }
        catch (HttpRequestException ex)
        {
            throw new EmicApiException(EmicApiErrorCode.Network, ex.Message);
        }

        using (response)
        {
            var body = response.Content == null
                ? string.Empty
                : await response.Content.ReadAsStringAsync(cancellationToken);

            if (response.StatusCode == HttpStatusCode.Unauthorized)
            {
                throw new EmicApiException(EmicApiErrorCode.Unauthorized, "Ogiltig eller återkallad token.");
            }

            if (response.StatusCode == HttpStatusCode.Forbidden)
            {
                throw new EmicApiException(EmicApiErrorCode.Forbidden, "Enheten saknar widget.read-behörighet.");
            }

            if (response.StatusCode == HttpStatusCode.NotFound)
            {
                throw new EmicApiException(EmicApiErrorCode.NotFound, "Resursen hittades inte.");
            }

            if (response.StatusCode == HttpStatusCode.TooManyRequests)
            {
                throw new EmicApiException(EmicApiErrorCode.RateLimited, "För många förfrågningar. Försök igen senare.");
            }

            if (!response.IsSuccessStatusCode)
            {
                throw new EmicApiException(
                    EmicApiErrorCode.Server,
                    $"Servern svarade med {(int)response.StatusCode}.");
            }

            try
            {
                var parsed = JsonSerializer.Deserialize<T>(body, JsonOptions);
                if (parsed == null)
                {
                    throw new EmicApiException(EmicApiErrorCode.InvalidResponse, "Tomt svar från servern.");
                }

                return parsed;
            }
            catch (JsonException ex)
            {
                throw new EmicApiException(EmicApiErrorCode.InvalidResponse, ex.Message);
            }
        }
    }

    public void Dispose() => _httpClient.Dispose();
}

public enum EmicApiErrorCode
{
    NotConfigured,
    Unauthorized,
    Forbidden,
    NotFound,
    RateLimited,
    Timeout,
    Network,
    Server,
    InvalidResponse,
}

public sealed class EmicApiException : Exception
{
    public EmicApiException(EmicApiErrorCode code, string message) : base(message)
    {
        Code = code;
    }

    public EmicApiErrorCode Code { get; }
}
