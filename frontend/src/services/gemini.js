import { GoogleGenAI } from "@google/genai";

const ai = new GoogleGenAI({
  apiKey: import.meta.env.VITE_GEMINI_API_KEY,
});

export const sendMessageToGemini = async (message) => {
  try {
    const response = await ai.models.generateContent({
      model: "gemini-3.6-flash",
      contents: message,
    });

    return response.text;
  } catch (error) {
    console.error("Gemini API Error:", error);
    throw new Error("Failed to get response from Gemini.");
  }
};