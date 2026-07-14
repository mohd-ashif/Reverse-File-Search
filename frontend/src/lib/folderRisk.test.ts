import { describe, expect, it } from "vitest";

import {
  RECOMMENDATION_HIGH,
  RECOMMENDATION_LOW,
  RECOMMENDATION_MEDIUM,
  classifyFolderRisk,
  isFolderPathTooBroad,
} from "@/lib/folderRisk";

const HIGH_RISK_PATHS = [
  "C:\\",
  "D:\\",
  "E:\\",
  "C:/",
  "/",
  "C:\\Windows",
  "C:\\Program Files",
  "C:\\Program Files (x86)",
  "C:\\ProgramData",
  "C:\\Users",
  "C:\\Users\\ADMIN",
  "C:\\Users\\Ashif",
  "C:\\Users\\ADMIN\\AppData",
  "C:\\Users\\ADMIN\\OneDrive",
  "C:\\Users\\ADMIN\\OneDrive - Bizpole",
  "/home",
  "/root",
  "/etc",
  "/usr",
  "/home/ashif",
  "/System",
  "/Applications",
  "/private",
  "/Users",
  "/Users/ashif",
];

const MEDIUM_RISK_PATHS = [
  "C:\\Users\\ADMIN\\Desktop",
  "C:\\Users\\ADMIN\\Downloads",
  "C:\\Users\\ADMIN\\Documents",
  "C:\\Users\\ADMIN\\Pictures",
  "/Users/ashif/Desktop",
  "/Users/ashif/Downloads",
  "/home/ashif/Documents",
  "/home/ashif/Pictures",
];

const LOW_RISK_PATHS = [
  "C:\\Users\\ADMIN\\Documents\\Reports",
  "D:\\MT\\calendar-reminder",
  "D:\\Projects",
  "C:\\Invoices",
  "C:\\Users\\ADMIN\\Documents\\CompanyData",
  "/home/ashif/Projects",
  "/Users/ashif/Documents/Archives",
  "C:\\Uploads",
];

describe("classifyFolderRisk", () => {
  it.each(HIGH_RISK_PATHS)("classifies %s as high risk and blocks it", (path) => {
    const assessment = classifyFolderRisk(path);
    expect(assessment.level).toBe("high");
    expect(assessment.recommendation).toBe(RECOMMENDATION_HIGH);
    expect(assessment.reason).toBeTruthy();
    expect(isFolderPathTooBroad(path)).toBe(true);
  });

  it.each(MEDIUM_RISK_PATHS)("classifies %s as medium risk but allows it", (path) => {
    const assessment = classifyFolderRisk(path);
    expect(assessment.level).toBe("medium");
    expect(assessment.recommendation).toBe(RECOMMENDATION_MEDIUM);
    expect(isFolderPathTooBroad(path)).toBe(false);
  });

  it.each(LOW_RISK_PATHS)("classifies %s as low risk", (path) => {
    const assessment = classifyFolderRisk(path);
    expect(assessment.level).toBe("low");
    expect(assessment.recommendation).toBe(RECOMMENDATION_LOW);
    expect(isFolderPathTooBroad(path)).toBe(false);
  });

  it("treats empty input as high risk", () => {
    expect(classifyFolderRisk("").level).toBe("high");
    expect(isFolderPathTooBroad("   ")).toBe(true);
  });

  it("catches traversal via the resolved path even when raw input looks fine", () => {
    const assessment = classifyFolderRisk("C:\\Users\\ADMIN\\Documents\\..\\..\\Windows", "C:\\Windows");
    expect(assessment.level).toBe("high");
  });

  it("does not over-block a legit resolved subfolder", () => {
    const assessment = classifyFolderRisk("D:\\MT\\calendar-reminder", "D:\\MT\\calendar-reminder");
    expect(assessment.level).toBe("low");
  });
});
