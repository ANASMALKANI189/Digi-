import axios from "axios";

const API_URL = "http://127.0.0.1:8000";


export const chatWithDigiMan = async (conversationId, message) => {
  const response = await axios.post(`${API_URL}/chat`, {
    conversation_id: conversationId,
    message: message,
  });

  return response.data;
};