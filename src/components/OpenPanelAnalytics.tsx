import { OpenPanelComponent } from "@openpanel/nextjs";

const provider = process.env.NEXT_PUBLIC_ANALYTICS_EVENTS_PROVIDER ?? "openpanel";
const clientId = process.env.NEXT_PUBLIC_OPENPANEL_CLIENT_ID;
const apiUrl = process.env.NEXT_PUBLIC_OPENPANEL_API_URL;
const scriptUrl = process.env.NEXT_PUBLIC_OPENPANEL_SCRIPT_URL;

export default function OpenPanelAnalytics() {
  if (provider !== "openpanel" || !clientId) return null;

  return (
    <OpenPanelComponent
      clientId={clientId}
      trackScreenViews={true}
      trackOutgoingLinks={true}
      trackAttributes={true}
      apiUrl={apiUrl}
      scriptUrl={scriptUrl}
      globalProperties={{
        app: "crisis_damage_intelligence",
        data_scope: "emsr884_venezuela",
        public_static: true,
      }}
    />
  );
}
