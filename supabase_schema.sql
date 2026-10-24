-- ============================================================
-- Little Store – full schema
-- Run this whole file in Supabase Dashboard > SQL Editor.
-- Safe to re-run: uses IF NOT EXISTS / ON CONFLICT.
-- ============================================================

create extension if not exists pgcrypto;

-- ── products ─────────────────────────────────────────────────
create table if not exists public.products (
  id              uuid        primary key default gen_random_uuid(),
  name            text        not null,
  description     text        not null default '',
  price           numeric(12,2)           check (price >= 0),  -- NULL = "Contact for price"
  original_price  numeric(12,2)           check (original_price >= 0), -- NULL = not on sale
  category        text,
  active          boolean     not null default true,
  created_at      timestamptz not null default now()
);

-- add columns to existing tables without breaking them
alter table public.products
  alter column price drop not null;

do $$
begin
  if not exists (
    select 1 from information_schema.columns
    where table_schema='public' and table_name='products' and column_name='original_price'
  ) then
    alter table public.products add column original_price numeric(12,2) check (original_price >= 0);
  end if;
end$$;

-- ── product_media ─────────────────────────────────────────────
create table if not exists public.product_media (
  id          uuid        primary key default gen_random_uuid(),
  product_id  uuid        not null references public.products(id) on delete cascade,
  file_path   text        not null,
  file_url    text        not null,
  media_type  text        not null check (media_type in ('image','video')),
  caption     text,
  sort_order  integer     not null default 0,
  is_primary  boolean     not null default false,
  created_at  timestamptz not null default now()
);

do $$
begin
  if not exists (
    select 1 from information_schema.columns
    where table_schema='public' and table_name='product_media' and column_name='sort_order'
  ) then
    alter table public.product_media add column sort_order integer not null default 0;
  end if;
end$$;

-- ── orders ────────────────────────────────────────────────────
create table if not exists public.orders (
  id              uuid        primary key default gen_random_uuid(),
  order_code      text        not null unique,
  customer_name   text        not null,
  phone           text        not null,
  address         text        not null,
  instructions    text,
  total_amount    numeric(12,2) not null check (total_amount >= 0),
  payment_method  text        not null default 'COD' check (payment_method = 'COD'),
  payment_status  text        not null default 'pending'
                    check (payment_status in ('pending','paid','not_collected')),
  status          text        not null default 'pending'
                    check (status in ('pending','confirmed','processing','shipped','delivered','cancelled')),
  created_at      timestamptz not null default now()
);

-- ── order_items ───────────────────────────────────────────────
create table if not exists public.order_items (
  id            uuid        primary key default gen_random_uuid(),
  order_id      uuid        not null references public.orders(id) on delete cascade,
  product_id    uuid        references public.products(id) on delete set null,
  product_name  text        not null,
  unit_price    numeric(12,2) not null check (unit_price >= 0),
  quantity      integer     not null check (quantity > 0),
  line_total    numeric(12,2) not null check (line_total >= 0)
);

-- ── Row Level Security ────────────────────────────────────────
alter table public.products      enable row level security;
alter table public.product_media enable row level security;
alter table public.orders        enable row level security;
alter table public.order_items   enable row level security;

drop policy if exists "Public can view active products"            on public.products;
drop policy if exists "Public can view media for active products"  on public.product_media;

create policy "Public can view active products" on public.products
  for select to anon, authenticated using (active = true);

create policy "Public can view media for active products" on public.product_media
  for select to anon, authenticated using (
    exists (select 1 from public.products p where p.id = product_id and p.active = true)
  );

-- ── Storage bucket ────────────────────────────────────────────
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'product-media',
  'product-media',
  true,
  52428800,
  array['image/jpeg','image/png','image/webp','image/gif','video/mp4','video/webm','video/quicktime']
)
on conflict (id) do update set
  public             = excluded.public,
  file_size_limit    = excluded.file_size_limit,
  allowed_mime_types = excluded.allowed_mime_types;
