import { handleInternalRequest } from "@/lib/api/internal-handler";
import { parseAoiIdParam, parsePriorityParams, priorityPayload } from "@/lib/data/internal-api-data";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET(request: Request) {
  return handleInternalRequest(request, () => {
    const searchParams = new URL(request.url).searchParams;
    const id = parseAoiIdParam(searchParams);
    const query = parsePriorityParams(searchParams);
    return priorityPayload(id, query);
  });
}
