export interface ApiErrorDetail {
  message: string;
  code?: string;
  dependent_modules?: string[];
  missing_capabilities?: string[];
  field_errors?: Record<string, string>;
}

export class ApiRequestError extends Error {
  readonly status: number;
  readonly detail: ApiErrorDetail;

  constructor(status: number, detail: ApiErrorDetail) {
    super(detail.message);
    this.name = "ApiRequestError";
    this.status = status;
    this.detail = detail;
  }
}

function normalizeDetail(raw: unknown, status: number): ApiErrorDetail {
  if (typeof raw === "string") {
    return { message: raw };
  }
  if (raw && typeof raw === "object") {
    const obj = raw as Record<string, unknown>;
    const message =
      typeof obj.message === "string"
        ? obj.message
        : typeof obj.detail === "string"
          ? obj.detail
          : `HTTP ${status}`;
    return {
      message,
      code: typeof obj.code === "string" ? obj.code : undefined,
      dependent_modules: Array.isArray(obj.dependent_modules)
        ? obj.dependent_modules.filter((item): item is string => typeof item === "string")
        : undefined,
      missing_capabilities: Array.isArray(obj.missing_capabilities)
        ? obj.missing_capabilities.filter((item): item is string => typeof item === "string")
        : undefined,
      field_errors:
        obj.field_errors && typeof obj.field_errors === "object"
          ? (Object.fromEntries(
              Object.entries(obj.field_errors as Record<string, unknown>).filter(
                (entry): entry is [string, string] => typeof entry[1] === "string",
              ),
            ) as Record<string, string>)
          : undefined,
    };
  }
  return { message: `HTTP ${status}` };
}

export async function parseApiError(res: Response): Promise<ApiRequestError> {
  const text = await res.text();
  try {
    const body = JSON.parse(text) as { detail?: unknown };
    return new ApiRequestError(res.status, normalizeDetail(body.detail ?? text, res.status));
  } catch {
    return new ApiRequestError(res.status, { message: text || `HTTP ${res.status}` });
  }
}

export function formatDependencyConflict(detail: ApiErrorDetail, moduleNames?: Record<string, string>): string {
  const lines = [detail.message];
  if (detail.dependent_modules?.length) {
    lines.push(
      "",
      "Krävs av:",
      ...detail.dependent_modules.map((id) => `• ${moduleNames?.[id] ?? id}`),
    );
  }
  return lines.join("\n");
}

export async function readApiError(res: Response): Promise<string> {
  const err = await parseApiError(res);
  return err.detail.message;
}
