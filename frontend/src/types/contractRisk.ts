export interface ContractRiskFlag {
  risk: string;
  present: boolean;
  explanation: string;
}

export interface ContractRiskAnalysis {
  file_id: number;
  filename: string;
  risks: ContractRiskFlag[];
}
