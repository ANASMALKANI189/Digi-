import { useEffect, useState } from "react";
import {
  loadAcademicRecord,
  saveAcademicRecord,
} from "../services/academicRecord";

export function useAcademicRecord() {
  const [academicData, setAcademicData] = useState(loadAcademicRecord);

  useEffect(() => {
    saveAcademicRecord(academicData);
  }, [academicData]);

  return {
    academicData,
    setAcademicData,
  };
}