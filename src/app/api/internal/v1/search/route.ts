import { handleInternalRequest } from "@/lib/api/internal-handler";
import { parseSearchParams, searchPayload } from "@/lib/data/internal-api-data";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET(request: Request) {
  return handleInternalRequest(request, () => {
    const query = parseSearchParams(new URL(request.url).searchParams);
    return searchPayload(query);
  });
}
