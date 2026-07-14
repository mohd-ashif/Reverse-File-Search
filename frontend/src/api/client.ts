import axios, { AxiosError } from "axios";

export interface FieldError {
  field: string;
  message: string;
}

export class ApiError extends Error {
  readonly status: number | null;
  readonly fieldErrors: FieldError[];

  constructor(message: string, status: number | null, fieldErrors: FieldError[] = []) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.fieldErrors = fieldErrors;
  }
}

interface FastApiValidationDetail {
  loc: (string | number)[];
  msg: string;
  type: string;
}

function messageForStatus(status: number | null): string {
  switch (status) {
    case 400:
      return "The request was invalid.";
    case 401:
      return "You are not authorized to perform this action.";
    case 403:
      return "You don't have permission to perform this action.";
    case 404:
      return "The requested resource was not found.";
    case 409:
      return "This conflicts with existing data.";
    case 422:
      return "Some fields failed validation.";
    case 423:
      return "That folder is currently locked and cannot be accessed.";
    case 500:
      return "Something went wrong on the server. Please try again.";
    case 503:
      return "That location is currently unreachable. Please check the connection and try again.";
    case null:
      return "Network error — check your connection and that the server is running.";
    default:
      return "An unexpected error occurred.";
  }
}

function parseError(error: AxiosError): ApiError {
  if (error.code === "ECONNABORTED") {
    return new ApiError("The request timed out. Please try again.", null);
  }

  if (!error.response) {
    return new ApiError(messageForStatus(null), null);
  }

  const { status, data } = error.response;
  const detail = (data as { detail?: unknown } | undefined)?.detail;

  if (Array.isArray(detail)) {
    const fieldErrors: FieldError[] = (detail as FastApiValidationDetail[]).map((item) => ({
      field: item.loc.filter((part) => part !== "body").join(".") || "value",
      message: item.msg,
    }));
    return new ApiError(messageForStatus(status), status, fieldErrors);
  }

  if (typeof detail === "string" && detail.length > 0) {
    return new ApiError(detail, status);
  }

  return new ApiError(messageForStatus(status), status);
}

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 30_000,
});

apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => Promise.reject(parseError(error))
);
