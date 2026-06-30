import { checkInternalApiAuth } from "@/lib/api/internal-auth";
import { internalError, internalJson, InternalApiHttpError } from "@/lib/api/internal-response";

export async function handleInternalRequest<T>(request: Request, handler: () => Promise<T> | T) {
  const authFailure = checkInternalApiAuth(request);
  if (authFailure) {
    return internalError(authFailure.status, authFailure.code, authFailure.message);
  }

  try {
    const data = await handler();
    return internalJson(data);
  } catch (error) {
    if (error instanceof InternalApiHttpError) {
      return internalError(error.status, error.code, error.message, error.details);
    }

    return internalError(
      500,
      "internal_server_error",
      "Internal API request failed.",
      error instanceof Error ? { name: error.name, message: error.message } : undefined,
    );
  }
}
