import { handleInternalRequest } from "@/lib/api/internal-handler";
import { summaryPayload } from "@/lib/data/internal-api-data";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET(request: Request) {
  return handleInternalRequest(request, summaryPayload);
}
