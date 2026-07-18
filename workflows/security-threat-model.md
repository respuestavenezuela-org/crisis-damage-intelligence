# Security Threat Model

## Goal

Prevent the WhatsApp crisis ops bot from becoming a source of harm, exploitation, doxxing, theft, misinformation, or unsafe movement during a crisis.

The system must assume that not every user is acting in good faith.

## Core Principle

Collect the minimum needed to coordinate, share even less by default, and require trusted human approval before exposing sensitive operational details.

## Threats

### Malicious Resource Seeking

Someone may ask where valuable resources are located in order to steal, block, exploit, or misdirect them.

Examples:

- fuel/gasoil
- generators
- Starlink units
- medical supplies
- tools
- machinery
- food stockpiles

### False Reports

Someone may submit fake needs, fake offers, fake resolved statuses, or fake route/resource updates.

### Doxxing And Retaliation

Someone may expose private names, phone numbers, home addresses, exact shelter locations, or vulnerable people.

### Unsafe Movement

The bot may accidentally tell people to move toward dangerous, blocked, unstable, or restricted areas.

### Operational Leakage

Sensitive details may leak from coordinator chats or exports into public responses.

### Impersonation

Someone may claim to be a coordinator, center operator, rescuer, or official source.

## Default Visibility Rules

All new records default to:

- `verification_status=unverified`
- `public_visibility=private`
- exact submitted locations stored as `private_sensitive`

The bot may acknowledge that a report was received, but must not publicly expose:

- exact private locations
- phone numbers
- names of vulnerable people
- high-value resource locations
- fuel quantities
- equipment inventories
- private access instructions
- security conditions
- medical/missing-person information

## Contact Data Minimization

The bot must not ask for the reporter's name by default.

The WhatsApp phone number is enough for private internal follow-up, but it must not appear in public exports, public search results, map data, or broad digests.

If follow-up is needed, ask permission:

```text
¿Coordinación puede contactarte por este WhatsApp si hace falta aclarar algo?
```

Do not ask for alternate phone numbers unless a coordinator explicitly needs one and the reason is recorded.

## Minimum Intake Vs Sharing

Minimum intake can be very small:

- what is needed/offered
- where it is, using a reference point if possible

But public sharing requires more review.

The system should accept incomplete reports, then route them to humans rather than pressuring vulnerable people for extra details.

## Trust Levels

V1 should support at least:

- `unknown`
- `known_reporter`
- `trusted_coordinator`
- `admin`

Trust level affects what the person can see and do, not whether their report is accepted.

Unknown users can:

- report needs
- report offers
- submit updates
- ask broad questions
- send voice, image, location, or documents as supporting evidence

Unknown users cannot:

- see exact sensitive resource locations
- mark records confirmed
- close records created by others unless reviewed
- overwrite canonical record fields
- access private contact details
- trigger public export

## Open Intake Rule

The WhatsApp number is intentionally open for intake. Any person with the number can message it.

The security boundary is not "who may submit"; it is "what happens after submission":

- new submissions are unverified
- new submissions are private
- updates are append-only until reviewed
- closure suggestions require review unless submitted by an authorized role
- sensitive lookups are redacted
- confirmation requires future role policy
- public sharing requires explicit approval

## Safe Response Patterns

For sensitive search results, answer with a safe routing response:

```text
Hay información relacionada, pero no puedo compartir detalles por aquí.
Dejo tu solicitud para coordinación. Código: REQ-184.
```

For high-value resources:

```text
Puedo registrar la necesidad de gasoil, pero la ubicación de recursos de combustible solo se comparte por coordinación verificada.
```

For exact locations:

```text
Recibí la ubicación. La mantendré privada hasta que coordinación decida qué se puede compartir.
```

## Exact Location Security

Exact coordinates and precise addresses may be stored because they can be operationally necessary.

They must be treated as sensitive data:

- private by default
- accessible only to authorized coordinator/admin roles
- excluded from public search, public summaries, and map exports by default
- replaced with approximate zone text in public outputs
- audited whenever viewed, exported, or shared
- never included in broad WhatsApp replies to unknown users

Recommended storage fields:

- `location_lat`
- `location_lng`
- `location_precision=exact`
- `location_access_level=private_sensitive`
- `public_location_text`, such as "Macuto", "La Guaira", or "cerca de Altamira"

Only a trusted coordinator/admin should be able to change `location_access_level` to `approved_public_exact`.

## Approval Requirements

Admin or trusted coordinator approval required before:

- sharing exact locations
- sharing private contacts
- sharing high-value resource availability
- publishing records to the map
- marking a record confirmed
- connecting requester and provider directly
- broad-broadcasting summaries

## Audit Requirements

Audit every:

- status change
- visibility change
- confirmation
- accepted/rejected update
- export
- private detail access
- exact location access
- direct match/contact share
- admin override

## Acceptance Criteria

- New records are private and unverified by default.
- Unknown users can submit but cannot access sensitive data.
- Search responses redact high-risk details.
- Exact coordinates are never public by default.
- Exact coordinates are stored only as private sensitive data and access is audited.
- Confirmation and visibility changes are audited.
- The system can operate with future role policy without redesign.
