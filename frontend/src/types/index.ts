export interface User { id: number; email: string; full_name: string; is_demo: boolean; created_at: string }
export interface Totals {
  planned_oil: number; actual_oil: number; net_shortfall: number; positive_shortfall: number; revenue: number; operating_cost: number;
  operating_profit: number; revenue_loss: number; downtime_hours: number; achievement_pct: number | null; loss_pct: number | null; record_count: number;
}
export const WELL_TYPES = ["VERTICAL", "HORIZONTAL", "DIRECTIONAL", "OFFSHORE"];
export const WELL_STATUSES = ["ACTIVE", "SHUT_IN", "MAINTENANCE", "ARCHIVED"];
export const LOSS_CATEGORIES = ["EQUIPMENT_FAILURE", "MAINTENANCE", "POWER_OUTAGE", "WELL_INTERVENTION", "WEATHER", "PROCESS_CONSTRAINT", "OTHER"];
