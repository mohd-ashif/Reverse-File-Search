export interface ExtractedText {
  file_id: number;
  filename: string;
  corrected_text: string | null;
  was_corrected: boolean;
}
