import { handleInternalRequest } from "@/lib/api/internal-handler";
import { parsePriorityParams, priorityPayload } from "@/lib/data/internal-api-data";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET(request: Request, { params }: { params: Promise<{ id: string }> }) {
  return handleInternalRequest(request, async () => {
    const { id } = await params;
    const query = parsePriorityParams(new URL(request.url).searchParams);
    return priorityPayload(id, query);
  });
}
