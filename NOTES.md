# Operational Notes

## Context

- Project: Respuesta Venezuela / crisis damage intelligence platform.
- Current public app is a static-first Next.js crisis map focused on the June 24, 2026 Venezuela earthquake response.
- Primary field constraints: modest Android phones, high latency, intermittent internet, low bandwidth.
- Existing platform value: Copernicus EMS damage context, AOI navigation, before/after evidence where safe, VLM/evidence queues for triage.
- New request under analysis: a WhatsApp-first coordination workflow for logistics and field support, potentially leveraging the separate Frontera WhatsApp bot platform.

## People And Terms

- Luis: builder/operator coordinating from outside Venezuela.
- Topos/rescatistas: field rescue teams; need practical, current, low-friction support.
- Centros de acopio: supply collection/distribution points.
- Coordinadores: humans who verify, route, and close requests.
- Starlink/conectividad: high-value operational resource because contact with field teams is unreliable.
- First real bot users: coordinators, logistics operators, and center-of-acopio operators. Rescuers are beneficiaries and occasional consumers, not the primary data-entry users.

## Signals From Conversations

- A field-adjacent coordinator said the current map is not the most useful immediate surface for her workflow.
- The urgent need is not another app or page; it is ordering logistics and knowing which tools/resources are current.
- WhatsApp is the real operating channel. Any solution should keep people inside WhatsApp where possible.
- July 1 transcript sharpened the goal: give one WhatsApp number to trusted field people, field-adjacent contacts, and resource holders such as centros de acopio so the system can automatically match needs and offers.
- The intended matching layer may use embeddings and a stronger AI model, but the product behavior should feel like natural-language WhatsApp, not command-only intake.
- A follow-up discussion set priorities: WhatsApp verification "over the data" can help manual verification, but it is lower priority than routing volunteers, insumos, gasolina, and maquinaria to verified requests.
- Current implementation risk reported by the team: the admin dashboard/matching path is "medio roto" because match completion is waiting for coordinator approval. The spec must make pending coordinator approval an explicit queue state, not a hidden failure.
- Needed resource categories mentioned: water, food, gasoil, tools, centers of collection/distribution, Starlink/connectivity, and existing tools that are actually updated.
- The map should remain a support surface, not the primary interface for logistics intake.
- Any AI-generated or external-source information must remain triage/evidence only, not official verification.
- Separate rescue-support feedback: rescatistas may need a digested, updated, copyable WhatsApp "ficha operativa" per building/person. This is not "more map"; it is private operational packaging of building, location, last signal of life, contact/source, event history, status, and map link.
- Rescue ficha data may include PII and life/death information, so it should not live as open public map data. Treat it as a private/high-risk workflow with redaction and access controls.
- July 2 transcript sharpened matching: do not auto-connect people. Show possible matches to coordinators even when there is only one useful overlap, nearby zones, or a transport gap. The coordinator decides whether the route is valid.
- Transport is a first-class bottleneck. A useful route may be triadic: need plus offer/resource plus trusted transport.
- The pilot network is currently tiny and trust-seeded manually: roughly one known transport contact, one rescue/brigade group, and no confirmed centers of acopio at the time of the transcript. Avoid overbuilding broad self-registration before this loop works.
- A coordinator asked whether the system records who matched cases. This must be explicit audit history: who approved/rejected/fulfilled/connected a match, when, and against which need/offer/transport records.

## Candidate System Shape

- WhatsApp-first intake and coordination bot.
- Converts free-form messages into structured operational records.
- Supports simple commands such as NECESITO, OFREZCO, BUSCAR, ACTUALIZAR, RESUELTO, HERRAMIENTAS.
- Human verification remains required for sensitive or high-impact actions.
- Primary intake should target logistics/resource operators, not rescuers in active field operations.
- Intake may remain open to anyone who has the WhatsApp number, but the latest preferred V1 policy is closed-for-routing: unknown contacts create review-only evidence until a coordinator validates the contact or record for internal routing.
- Anyone can submit updates on existing records, but updates do not overwrite the record directly. Unknown users cannot close records; closure becomes pending review.
- Bot should detect duplicates, ask only minimal follow-up questions, preserve source/provenance, and generate coordinator handoff summaries.
- Frontera may provide reusable backend capabilities: WhatsApp webhook, conversation continuity, media handling, deduplication, sanitization, 24-hour session handling, templates, admin inbox, KB, and human handoff.
- Architecture decision: leverage Frontera as the WhatsApp/backoffice system of record. Do not rebuild webhook/admin/conversation storage in the public map repo unless Frontera becomes unavailable.
- V1 does not require export to the public map. V1 scope is WhatsApp/Frontera intake and coordination. Public/static map export is P1 after confirmed data and publishing policy exist.
- V1 core acceptance gate: a natural-language need/offer message must create a record, create explainable match recommendations, show pending coordinator approval in the action queue, and let an authorized coordinator approve/reject the route without exposing private details by default.
- Button/menu UX is useful but secondary. First battle-test natural-language intake, matching, and coordinator approval; add buttons only after that loop is reliable.
- WhatsApp bot replies should be concrete, human-but-structured, easy to scan, and fit in one message by default. Preserve context instead of cutting it; split into multiple WhatsApp messages only when a real limit or safety need makes one message impractical. The old "split messages to feel human" behavior is not the preferred V1 behavior.
- WhatsApp data verification is a deferred workflow. Do not let it interrupt the resource-routing MVP unless routing is already passing the V1 gate above.
- Implementation gap backlog lives in `workflows/frontera-crisis-ops-implementation-gap-issues.md`.

## Workflow Suite

- Frontera Crisis Ops Bot Spec: final consolidated V1 implementation spec for building the WhatsApp coordination MVP inside Frontera.
- Rescue Operational Card: adjacent high-risk workflow for private building/person rescue summaries that are copyable to WhatsApp; not automatically part of logistics V1.
- WhatsApp Resource Intake: turn incoming needs/offers/updates/resolutions into structured records.
- WhatsApp Resource Search: answer resource/tool searches from safe current records.
- Resource Verification And Routing: coordinator queue for confirmation, rejection, routing, and escalation.
- Need Offer Matching: recommend compatible need/offer/resource matches without exposing private details automatically.
- Tool Directory Freshness: maintain a current list of crisis tools and their status.
- Coordinator Handoff Digest: periodic/on-demand operational summaries for shift changes and overloaded coordinators.
- WhatsApp Voice And Media Intake: convert voice notes, images, locations, documents, and contacts into candidate records.
- Verified Data Export To Public Map: P1, after confirmed data and publication policy exist.
- WhatsApp Data Verification: P2/deferred until the resource-routing loop is reliable; creates verification events, not automatic official claims.
- WhatsApp Response Contract: the outbound-message loop that keeps bot replies concrete, formatted, context-preserving, and one-message-by-default.
- Coordinator Operational Console: action queue for critical items, verification, duplicates, matches, stale data, bottlenecks, sensitive access, and public-safe sharing.
- Frontera Leverage Plan: mapping from existing Frontera WhatsApp/commercial bot capabilities to the crisis ops MVP.
- V1 Data Model: minimum Frontera-side entities for crisis intake, coordination, matching, tool freshness, and sensitive access audit.

## Coordinator Research Notes

- Coordinators need resource request fields: what/quantity/type, location, priority, suggested sources/substitutes, supplier/contact, notes, and approval state.
- They need status snapshots and resource status changes rather than raw chat.
- They need information management that identifies gaps, bottlenecks, duplicate effort, and roles/responsibilities.
- They need data protection because both personal and non-personal operational data can be sensitive.
- They need match approval to be visible and fast. If a match cannot complete because approval is missing, the system should show a `review_match` or `approve_match_for_routing` queue item with the blocking reason.

## Safety Boundaries

- Do not collect or publish unnecessary PII.
- Do not ask for the reporter's name by default.
- Use the WhatsApp number as private internal contact metadata. Ask "¿pueden contactarte por este WhatsApp?" only when follow-up is needed.
- Do not expose private numbers, exact sensitive locations, or missing-person/medical data without a separate safety design.
- Exact locations may be stored when submitted, but they must be treated as secured sensitive data: private by default, role-restricted, audited on access, and approximated/redacted in public outputs.
- Keep status labels visible: unverified, needs verification, confirmed, stale, resolved.
- Human review required for emergency response, medical, missing persons, public claims, data verification, and anything safety-sensitive.
- Authority for marking records `confirmed` must be configurable, but V1 needs a provisional policy so matching is not blocked forever: trusted coordinators may confirm ordinary logistics/resource records for internal routing; admins retain public/export, role, official-damage, medical, missing-person, and other sensitive approvals.
- Assume some users may be malicious. Accept reports with low friction, but default new records to private/unverified and restrict access to high-value resource details.
- Anyone can submit information through WhatsApp, but unknown users cannot see private operational details or confirm records.
- For urgent/life-safety reports, register and escalate, but clearly state this is a citizen information coordination effort, not an official emergency service or response guarantee.
- Public map must continue working without the WhatsApp/Frontera system.

## Open Grilling Questions

- Confirmation authority model after V1 remains TBD by organization/category/geography. Recommended V1 answer: `trusted_coordinator` can approve ordinary logistics matches for internal routing; `admin` is required for public/export/official/sensitive actions.
- Exact export mechanism from Frontera to this static map repo is P1/TBD, not V1. Recommended V1 answer: no public map export until confirmed records and publication policy exist.
- Rescue Operational Card scope remains TBD. Recommended V1 answer: keep it separate from logistics V1 unless a rescue lead explicitly owns the safety workflow.
- Response format standardization remains a product choice. Recommended V1 answer: every intake receipt should use the same visible order: code, interpreted item, zone, status, coordination/privacy note, next action.
