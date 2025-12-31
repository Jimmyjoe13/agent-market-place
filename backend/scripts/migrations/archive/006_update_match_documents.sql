-- Migration: Mise à jour de match_documents pour supporter le multi-tenant
-- Date: 2024-12-26

-- Mise à jour de la fonction match_documents pour inclure le filtre user_id
create or replace function match_documents (
  query_embedding vector(1024),
  match_threshold float,
  match_count int,
  filter_source_type varchar default null,
  filter_user_id uuid default null
)
returns table (
  id uuid,
  content text,
  metadata jsonb,
  source_type varchar,
  source_id varchar,
  similarity float,
  user_id uuid
)
language plpgsql
as $$
begin
  return query
  select
    documents.id,
    documents.content,
    documents.metadata,
    documents.source_type,
    documents.source_id,
    1 - (documents.embedding <=> query_embedding) as similarity,
    documents.user_id
  from documents
  where 1 - (documents.embedding <=> query_embedding) > match_threshold
  and (filter_source_type is null or documents.source_type = filter_source_type)
  and (filter_user_id is null or documents.user_id = filter_user_id)
  order by documents.embedding <=> query_embedding
  limit match_count;
end;
$$;
