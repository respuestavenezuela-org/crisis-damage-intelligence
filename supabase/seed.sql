insert into activations (id, provider, code, name_en, name_es, status, source_url)
values (
  'emsr884',
  'copernicus-ems',
  'EMSR884',
  'Venezuela Earthquake EMSR884',
  'Terremoto Venezuela EMSR884',
  'active',
  'https://rapidmapping.emergency.copernicus.eu/backend/dashboard-api/public-activations/?code=EMSR884'
)
on conflict (id) do update set
  status = excluded.status,
  updated_at = now();

insert into aois (id, activation_id, aoi_number, name_en, name_es, status, priority, expected_delivery, static_catalog_path, metadata)
values
  (
    'emsr884-aoi02-caracas',
    'emsr884',
    2,
    'AOI02 Caracas - Official EMSR884 Vector',
    'AOI02 Caracas - Vector oficial EMSR884',
    'final',
    'normal',
    null,
    '/data/aoi/emsr884-aoi02-caracas',
    '{"features":17,"destroyed":0,"damaged":0,"possibly_damaged":17}'::jsonb
  ),
  (
    'emsr884-aoi06-moron',
    'emsr884',
    6,
    'AOI06 Moron - Official EMSR884 Vector',
    'AOI06 Moron - Vector oficial EMSR884',
    'final',
    'high',
    null,
    '/data/aoi/emsr884-aoi06-moron',
    '{"features":129,"destroyed":2,"damaged":34,"possibly_damaged":93}'::jsonb
  ),
  (
    'emsr884-aoi12-caraballeda',
    'emsr884',
    12,
    'AOI12 Caraballeda / La Guaira',
    'AOI12 Caraballeda / La Guaira',
    'waiting',
    'critical',
    '2026-06-27T01:00:00Z',
    null,
    '{"reason":"La Guaira / Caraballeda coastal damage gap"}'::jsonb
  )
on conflict (id) do update set
  status = excluded.status,
  priority = excluded.priority,
  expected_delivery = excluded.expected_delivery,
  metadata = excluded.metadata,
  updated_at = now();

insert into products (activation_id, aoi_id, product_type, product_code, status, version_label, source_file, source_layer, metadata)
values
  ('emsr884', 'emsr884-aoi02-caracas', 'GRA', 'EMSR884_AOI02_GRA_v1', 'final', 'v1', 'EMSR884_AOI02_GRA_PRODUCT_v1.gpkg', 'builtUpA_v1', '{"features":17,"destroyed":0,"damaged":0,"possibly_damaged":17}'::jsonb),
  ('emsr884', 'emsr884-aoi06-moron', 'GRA', 'EMSR884_AOI06_GRA_v1', 'final', 'v1', 'EMSR884_AOI06_GRA_PRODUCT_v1.gpkg', 'builtUpA_v1', '{"features":129,"destroyed":2,"damaged":34,"possibly_damaged":93}'::jsonb)
on conflict do nothing;

insert into ingestion_jobs (activation_id, aoi_id, job_type, status, output_prefix, metadata, started_at, finished_at)
values
  ('emsr884', 'emsr884-aoi02-caracas', 'seed-static-export', 'completed', 'public/data/aoi/emsr884-aoi02-caracas', '{"source":"packaged static EMSR884 acceptance"}'::jsonb, now(), now()),
  ('emsr884', 'emsr884-aoi06-moron', 'seed-static-export', 'completed', 'public/data/aoi/emsr884-aoi06-moron', '{"source":"packaged static EMSR884 acceptance"}'::jsonb, now(), now())
on conflict do nothing;

insert into source_confidence_audit (entity_type, entity_id, source_type, confidence_label, statement, source_uri)
values
  ('aoi', 'emsr884-aoi02-caracas', 'official_ems_vector', 'source_of_record', 'Official Copernicus EMSR884 GRA builtUpA labels are the source of record for this AOI.', '/data/aoi/emsr884-aoi02-caracas/source_metadata.json'),
  ('aoi', 'emsr884-aoi06-moron', 'official_ems_vector', 'source_of_record', 'Official Copernicus EMSR884 GRA builtUpA labels are the source of record for this AOI.', '/data/aoi/emsr884-aoi06-moron/source_metadata.json'),
  ('activation', 'emsr884', 'operational_warning', 'do_not_overclaim', 'EMS builtUpA features may not be one building each; absence of marked features is not proof of no damage.', null)
on conflict do nothing;
