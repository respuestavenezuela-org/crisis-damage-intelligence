create extension if not exists postgis;
create extension if not exists pgcrypto;

create table if not exists activations (
  id text primary key,
  provider text not null default 'copernicus-ems',
  code text not null,
  name_en text not null,
  name_es text not null,
  status text not null,
  source_url text,
  updated_at timestamptz not null default now()
);

create table if not exists aois (
  id text primary key,
  activation_id text not null references activations(id) on delete cascade,
  aoi_number integer,
  name_en text not null,
  name_es text not null,
  country text not null default 'Venezuela',
  status text not null,
  priority text not null default 'normal',
  expected_delivery timestamptz,
  bounds geometry(Polygon, 4326),
  center geometry(Point, 4326),
  static_catalog_path text,
  metadata jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

create table if not exists products (
  id uuid primary key default gen_random_uuid(),
  activation_id text not null references activations(id) on delete cascade,
  aoi_id text not null references aois(id) on delete cascade,
  product_type text not null,
  provider text not null default 'copernicus-ems',
  product_code text,
  status text not null,
  version_label text,
  source_url text,
  download_url text,
  object_storage_uri text,
  source_file text,
  source_layer text,
  delivered_at timestamptz,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists ingestion_jobs (
  id uuid primary key default gen_random_uuid(),
  activation_id text references activations(id) on delete set null,
  aoi_id text references aois(id) on delete set null,
  product_id uuid references products(id) on delete set null,
  job_type text not null,
  status text not null default 'queued',
  source_url text,
  input_uri text,
  output_prefix text,
  started_at timestamptz,
  finished_at timestamptz,
  error text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists damage_features (
  id text primary key,
  activation_id text not null references activations(id) on delete cascade,
  aoi_id text not null references aois(id) on delete cascade,
  product_id uuid references products(id) on delete set null,
  source_feature_id text,
  object_type text,
  damage_gra text,
  damage_class text,
  damage_percent numeric,
  confidence numeric,
  source_label text not null default 'official_ems',
  validation_status text not null default 'unreviewed',
  geom geometry(Geometry, 4326),
  centroid geometry(Point, 4326),
  google_maps_url text,
  properties jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists vlm_review_queue (
  id uuid primary key default gen_random_uuid(),
  damage_feature_id text not null references damage_features(id) on delete cascade,
  status text not null default 'queued',
  priority integer not null default 100,
  model text,
  prompt_version text not null default 'before-after-damage-v1',
  chip_uri text,
  before_uri text,
  after_uri text,
  result jsonb,
  confidence numeric,
  error text,
  created_at timestamptz not null default now(),
  started_at timestamptz,
  finished_at timestamptz,
  updated_at timestamptz not null default now()
);

create table if not exists human_validations (
  id uuid primary key default gen_random_uuid(),
  damage_feature_id text not null references damage_features(id) on delete cascade,
  reviewer_id text,
  status text not null,
  validated_damage_class text,
  notes text,
  evidence_uri text,
  created_at timestamptz not null default now()
);

create table if not exists source_confidence_audit (
  id uuid primary key default gen_random_uuid(),
  entity_type text not null,
  entity_id text not null,
  source_type text not null,
  confidence_label text not null,
  confidence_score numeric,
  statement text not null,
  source_uri text,
  created_at timestamptz not null default now()
);

create index if not exists aois_activation_idx on aois (activation_id, status);
create index if not exists products_aoi_type_idx on products (aoi_id, product_type, status);
create index if not exists ingestion_jobs_status_idx on ingestion_jobs (status, created_at);
create index if not exists damage_features_geom_idx on damage_features using gist (geom);
create index if not exists damage_features_centroid_idx on damage_features using gist (centroid);
create index if not exists damage_features_aoi_damage_idx on damage_features (aoi_id, damage_gra, validation_status);
create index if not exists vlm_review_queue_status_priority_idx on vlm_review_queue (status, priority, created_at);
create index if not exists human_validations_feature_idx on human_validations (damage_feature_id, created_at desc);
create index if not exists source_confidence_entity_idx on source_confidence_audit (entity_type, entity_id, created_at desc);

alter table activations enable row level security;
alter table aois enable row level security;
alter table products enable row level security;
alter table ingestion_jobs enable row level security;
alter table damage_features enable row level security;
alter table vlm_review_queue enable row level security;
alter table human_validations enable row level security;
alter table source_confidence_audit enable row level security;

drop policy if exists public_read_activations on activations;
drop policy if exists public_read_aois on aois;
drop policy if exists public_read_products on products;
drop policy if exists public_read_damage_features on damage_features;
drop policy if exists public_read_completed_vlm on vlm_review_queue;
drop policy if exists public_read_validations on human_validations;
drop policy if exists public_read_confidence on source_confidence_audit;

create policy public_read_activations on activations for select using (true);
create policy public_read_aois on aois for select using (true);
create policy public_read_products on products for select using (true);
create policy public_read_damage_features on damage_features for select using (true);
create policy public_read_completed_vlm on vlm_review_queue for select using (status = 'completed');
create policy public_read_validations on human_validations for select using (true);
create policy public_read_confidence on source_confidence_audit for select using (true);
