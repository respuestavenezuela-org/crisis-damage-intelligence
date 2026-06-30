import { handleInternalRequest } from "@/lib/api/internal-handler";
import { aoisPayload } from "@/lib/data/internal-api-data";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET(request: Request) {
  return handleInternalRequest(request, aoisPayload);
}
