import { handleInternalRequest } from "@/lib/api/internal-handler";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET(request: Request) {
  return handleInternalRequest(request, () => ({
    status: "ok",
    service: "respuesta-venezuela-internal-api",
  }));
}
