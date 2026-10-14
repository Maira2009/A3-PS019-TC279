export type Page<T> = { items: T[]; total: number; limit?: number; offset?: number };
export type Workspace = { id: string; name: string; created_at: string; status: string };
export type Source = { id: string; workspace_id: string; display_name: string; source_type: string; file_size_bytes: number; status: string; warnings?: string[] };
export type Scan = { id: string; status: string; stage: string; summary?: Summary; started_at?: string; finished_at?: string };
export type Summary = { source_count: number; successful_source_count: number; object_count: number; profiled_field_count: number; finding_count: number; footprint_count: number; failed_sources: { source_id: string; source: string; error: string }[] };
export type Finding = {
  id: string; source_name: string; object_name: string; field_name: string; class_key: string;
  rule_strength: number; confidence_label: string; reason_codes?: string[]; explanation: string;
  masked_samples?: string[]; purpose_status: string; retention_status: string; metadata_scope?: string;
  review_status: string; rule_version: string;
};
export type Footprint = { id: string; class_key: string; masked_representative: string; source_count: number; occurrence_count: number; locations?: Record<string, unknown>[]; ambiguity_note: string; overlap_type: string; review_status: string };
export type Metadata = { id: string; source_id?: string; object_name?: string; field_name?: string; class_key?: string; purpose_text?: string; retention_duration?: string; retention_basis?: string; owner_label?: string };
export type Rule = { class_key: string; display_name: string; enabled: boolean; field_aliases: string[]; patterns: { name: string; regex: string }[]; field_name_weight: number; pattern_weight: number; type_weight: number; threshold: number; mask_strategy: string; notes: string; version?: string };
export type Evaluation = { id: string; labelled_count: number; caveat: string; per_class: Record<string, { tp: number; fp: number; fn: number; tn: number; precision: number | null; recall: number | null; support: number }> };

