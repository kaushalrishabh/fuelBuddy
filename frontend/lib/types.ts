export type EntryType = "refuel" | "fuel_removed";
export type FillType = "full" | "partial";
export type OdometerStatus = "ok" | "faulty" | "estimated";
export type EntrySource = "manual" | "excel" | "text_import";
export type OdometerEventType = "faulty_period" | "replaced" | "reset";
export type SegmentStatus = "valid" | "excluded_faulty" | "excluded_anomalous" | "estimated";

export interface User {
  id: number;
  email: string;
}

export interface Vehicle {
  id: number;
  name: string;
  make: string | null;
  model: string | null;
  purchase_date: string | null;
  tank_capacity_l: string;
  initial_odometer_km: string;
  is_default: boolean;
}

export interface Entry {
  id: number;
  vehicle_id: number;
  entry_type: EntryType;
  date: string;
  odometer_km: string | null;
  litres: string;
  amount_rs: string | null;
  price_per_litre: string | null;
  fill_type: FillType | null;
  location: string | null;
  station_name: string | null;
  notes: string | null;
  odometer_status: OdometerStatus;
  distance_override_km: string | null;
  source: EntrySource;
  raw_text: string | null;
  created_at: string;
  updated_at: string;
}

export interface EntryListResponse {
  items: Entry[];
  total: number;
  page: number;
  page_size: number;
}

export interface SuggestedFix {
  action: "mark_faulty" | "log_odometer_event" | "set_distance_override";
  label: string;
  prefill?: Record<string, string> | null;
}

export interface ValidationWarning {
  code: string;
  message: string;
  suggested_fixes: SuggestedFix[];
}

export interface FillPreview {
  distance_since_last_full_km: string | null;
  km_per_l: string | null;
  rs_per_km: string | null;
}

export interface EntrySaveResponse {
  entry: Entry;
  warnings: ValidationWarning[];
  preview: FillPreview | null;
}

export interface EntryPreviewResponse {
  warnings: ValidationWarning[];
  preview: FillPreview | null;
}

export interface OdometerEvent {
  id: number;
  vehicle_id: number;
  event_type: OdometerEventType;
  start_date: string;
  end_date: string | null;
  old_reading_at_change: string | null;
  new_reading_at_change: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface ParsedRow {
  row_number: number;
  raw_text: string;
  source: EntrySource;
  entry_type: EntryType | null;
  date: string | null;
  odometer_km: string | null;
  litres: string | null;
  amount_rs: string | null;
  price_per_litre: string | null;
  fill_type: FillType | null;
  location: string | null;
  station_name: string | null;
  odometer_status: OdometerStatus;
  distance_override_km: string | null;
  notes: string;
  errors: string[];
  warnings: string[];
  is_duplicate: boolean;
}

export interface ImportPreviewResponse {
  rows: ParsedRow[];
  valid_count: number;
  warning_count: number;
  error_count: number;
  duplicate_count: number;
}

export interface ImportCommitResponse {
  imported: number;
  skipped_duplicates: number;
  skipped_errors: number;
}

export interface KPIs {
  lifetime_km_per_l: string | null;
  last_fill_km_per_l: string | null;
  total_km: string;
  total_litres: string;
  litres_removed: string;
  total_spend_rs: string;
  average_rs_per_km: string | null;
  average_rs_per_l: string | null;
  days_since_last_fill: number | null;
}

export interface MileagePoint {
  date: string;
  km_per_l: string | null;
  rolling_avg_km_per_l: string | null;
  status: SegmentStatus;
}

export interface MonthlyPoint {
  year: number;
  month: number;
  litres: string;
  spend_rs: string;
  km: string;
  fill_count: number;
}

export interface PricePoint {
  date: string;
  price_per_litre: string;
}

export interface PriceTrend {
  points: PricePoint[];
  min_price: string | null;
  max_price: string | null;
  average_price: string | null;
}

export interface YearlySummary {
  year: number;
  km: string;
  litres: string;
  spend_rs: string;
  avg_km_per_l: string | null;
  avg_rs_per_l: string | null;
  fill_count: number;
}

export interface CostEfficiencyPoint {
  date: string;
  rs_per_km: string | null;
}

export interface CostEfficiency {
  points: CostEfficiencyPoint[];
  yearly_summary: YearlySummary[];
}

export interface RankedPlace {
  name: string;
  sample_size: number;
  avg_km_per_l: string;
  avg_rs_per_l: string | null;
}

export interface SeasonalityPoint {
  month: number;
  avg_km_per_l: string | null;
  sample_size: number;
}

export interface RidingPattern {
  avg_days_between_fills: string | null;
  avg_km_per_day: string | null;
  predicted_next_refuel_date: string | null;
}

export interface SegmentSummary {
  start_date: string;
  end_date: string;
  distance_km: string;
  km_per_l: string | null;
  rs_per_km: string | null;
  status: SegmentStatus;
}

export interface Records {
  best_mileage: SegmentSummary | null;
  worst_mileage: SegmentSummary | null;
  longest_distance: SegmentSummary | null;
  most_expensive_fill_entry_id: number | null;
  most_expensive_fill_amount_rs: string | null;
}

export interface DataQualityIssue {
  kind: string;
  message: string;
  entry_ids: number[];
}

export interface DataQualityReport {
  issues: DataQualityIssue[];
  excluded_segment_count: number;
  estimated_segment_count: number;
}

export type DateRangeType =
  | "last_3_months"
  | "last_6_months"
  | "last_12_months"
  | "calendar_year"
  | "all_time"
  | "custom";
