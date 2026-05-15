export interface Violation {
  id?: number;
  violation_code: string;
  violation_name: string;
  min_fine_local: number | null;
  max_fine_local: number | null;
  currency: string;
  mv_act_section: string | null;
  compounding_eligible: boolean;
  compounding_fee: number | null;
  category?: string;
  vehicle_type?: string;
  state_province?: string;
}

export interface CalculateRequest {
  violation_codes: string[];
  vehicle_type: string;
  country: string;
  state_province?: string;
  is_repeat_offense: boolean;
}

export interface CalculateResponse {
  currency: string;
  total_fine: number;
  compounding_available: boolean;
  total_compounding_fee: number;
  violations: {
    violation_code: string;
    violation_name: string;
    fine_amount: number;
    compounding_fee: number | null;
    is_compoundable: boolean;
  }[];
}
