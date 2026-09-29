import academicRecord from "../data";

const STORAGE_KEY = "academic_record";

export function loadAcademicRecord() {
  const saved = localStorage.getItem(STORAGE_KEY);

  if (!saved) {
    return academicRecord;
  }

  try {
    return JSON.parse(saved);
  } catch (error) {
    console.error("Failed to parse academic record:", error);
    return academicRecord;
  }
}

export function saveAcademicRecord(record) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(record));
  } catch (error) {
    console.error("Failed to save academic record:", error);
  }
}

export function resetAcademicRecord() {
  localStorage.removeItem(STORAGE_KEY);
  return academicRecord;
}
export function updateWadIse1(record, marks) {
  const updated = structuredClone(record);

  updated.subjects.sub_wad_502.assessments.ise_1.marks_obtained = marks;
  updated.subjects.sub_wad_502.assessments.ise_1.date =
    new Date().toISOString();

  return updated;
}