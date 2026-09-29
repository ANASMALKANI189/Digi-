import React, { useState, useRef, useEffect } from "react";
import {
  ArrowLeft,
  Mic,
  Send,
  RotateCcw,
  X,
  Sparkles,
} from "lucide-react";

import { chatWithDigiMan } from "../services/conversation";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";

import "katex/dist/katex.min.css";
import "../styles/AIChatBot.css";

// ---------------------------------------------------------------------------
// Fonts
// ---------------------------------------------------------------------------

const FONT_IMPORT =
  "@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600&display=swap');";

// ---------------------------------------------------------------------------
// Initial message
// ---------------------------------------------------------------------------

const seedMessages = [
  {
    id: "seed-1",
    role: "assistant",
    text: "Hello! How can I help you today?",
    timestamp: new Date().toISOString(),
  },
];

// ---------------------------------------------------------------------------
// Orb
// ---------------------------------------------------------------------------

function Orb({ active }) {
  return (
    <div className={`orb-wrap ${active ? "is-active" : ""}`}>
      <div className="orb-ring ring-1" />
      <div className="orb-ring ring-2" />
      <div className="orb-core" />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Typing dots
// ---------------------------------------------------------------------------

function TypingDots() {
  return (
    <div className="typing">
      <span />
      <span />
      <span />
    </div>
  );
}

// ---------------------------------------------------------------------------
// AI Component
// ---------------------------------------------------------------------------

export default function AI() {
  // ---------------------------------------------------------
  // UI state
  // ---------------------------------------------------------

  const [mode, setMode] = useState("voice");

  const [messages, setMessages] = useState(seedMessages);

  const [draft, setDraft] = useState("");

  const [thinking, setThinking] = useState(false);

  const [listening, setListening] = useState(true);

  const [conversationId, setConversationId] = useState(null);

  const scrollRef = useRef(null);

  // ---------------------------------------------------------
  // Auto-scroll chat
  // ---------------------------------------------------------

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop =
        scrollRef.current.scrollHeight;
    }
  }, [messages, thinking, mode]);

  // ---------------------------------------------------------
  // Send message
  // ---------------------------------------------------------

  const send = async (text) => {
    const trimmed = (text ?? draft).trim();

    if (!trimmed || thinking) return;

    // -------------------------------------------------------
    // Add user message immediately
    // -------------------------------------------------------

    const userMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      text: trimmed,
      timestamp: new Date().toISOString(),
    };

    setMessages((messages) => [
      ...messages,
      userMessage,
    ]);

    setDraft("");

    setThinking(true);

    // -------------------------------------------------------
    // Backend request
    // -------------------------------------------------------

    try {
      const result = await chatWithDigiMan(
        conversationId,
        trimmed
      );

      // -----------------------------------------------------
      // Save conversation ID
      // -----------------------------------------------------

      setConversationId(
        result.conversation_id
      );

      // -----------------------------------------------------
      // Add assistant response
      // -----------------------------------------------------

      const assistantMessage = {
        id: `assistant-${Date.now()}`,
        role: "assistant",
        text: result.response,
        timestamp: new Date().toISOString(),
      };

      setMessages((messages) => [
        ...messages,
        assistantMessage,
      ]);
    } catch (error) {
      console.error(
        "Chat error:",
        error
      );

      // -----------------------------------------------------
      // Error message
      // -----------------------------------------------------

      const errorMessage = {
        id: `assistant-error-${Date.now()}`,
        role: "assistant",
        text:
          "Sorry, I couldn't connect right now. Please try again.",
        timestamp: new Date().toISOString(),
      };

      setMessages((messages) => [
        ...messages,
        errorMessage,
      ]);
    } finally {
      setThinking(false);
    }
  };

  // ---------------------------------------------------------
  // Voice screen -> Chat screen
  // ---------------------------------------------------------

  const goToChatFromVoice = () => {
    setListening(false);

    setMode("chat");
  };

  // ---------------------------------------------------------
  // New conversation
  // ---------------------------------------------------------

  const resetConversation = () => {
    setMessages([
      {
        id: `seed-${Date.now()}`,
        role: "assistant",
        text: "Hello! How can I help you today?",
        timestamp: new Date().toISOString(),
      },
    ]);

    // null means next message creates new conversation
    setConversationId(null);
  };

  // ---------------------------------------------------------
  // Render
  // ---------------------------------------------------------

  return (
    <div className="app-shell">
      <style>
        {`
          ${FONT_IMPORT}
        `}
      </style>

      <div className="phone">

        {/* =====================================================
            VOICE SCREEN
            ===================================================== */}

        {mode === "voice" ? (
          <div className="voice-screen">

            {/* Top Bar */}

            <div
              className="topbar"
              style={{ width: "100%" }}
            >
              <button
                className="icon-btn"
                onClick={goToChatFromVoice}
                aria-label="Back to chat"
              >
                <ArrowLeft size={16} />
              </button>

              <div className="topbar-title">

                <span className="name">
                  Speaking to Nova
                </span>

                <span className="status">
                  <span className="status-dot" />

                  {listening
                    ? "Listening"
                    : "Idle"}
                </span>

              </div>

              <button
                className="icon-btn"
                onClick={() =>
                  setListening(
                    (value) => !value
                  )
                }
                aria-label="Toggle listening"
              >
                <Sparkles size={15} />
              </button>

            </div>

            {/* Voice Heading */}

            <div className="voice-heading">
              <p>
                {listening
                  ? "Go ahead, I'm listening…"
                  : "Tap the mic to talk"}
              </p>
            </div>

            {/* Orb */}

            <div className="orb-stage">
              <Orb active={listening} />
            </div>

            {/* Last Query */}

            <div className="last-query">
              Start talking to{" "}
              <span className="hl">
                Digiमन
              </span>
            </div>

            {/* Voice Controls */}

            <div className="voice-controls">

              <button
                className="ghost-btn"
                onClick={goToChatFromVoice}
                aria-label="Switch to text chat"
              >
                <X size={16} />
              </button>

              <button
                className="mic-btn"
                onClick={() =>
                  setListening(
                    (value) => !value
                  )
                }
                aria-label="Toggle microphone"
              >
                <Mic size={22} />
              </button>

              <button
                className="ghost-btn"
                onClick={goToChatFromVoice}
                aria-label="Open transcript"
              >
                <ArrowLeft
                  size={16}
                  style={{
                    transform:
                      "rotate(180deg)",
                  }}
                />
              </button>

            </div>
          </div>

        ) : (

          /* =====================================================
             CHAT SCREEN
             ===================================================== */

          <div className="chat-screen">

            {/* =================================================
                TOP BAR
                ================================================= */}

            <div className="topbar">

              <button
                className="icon-btn"
                onClick={() =>
                  setMode("voice")
                }
                aria-label="Back to voice"
              >
                <ArrowLeft size={16} />
              </button>

              <div className="topbar-title">

                <span className="name">
                  Digiमन
                </span>

                <span className="status">
                  <span className="status-dot" />
                  Online
                </span>

              </div>

              <button
                className="icon-btn"
                onClick={resetConversation}
                aria-label="Reset conversation"
              >
                <RotateCcw size={14} />
              </button>

            </div>

            {/* =================================================
                MESSAGES
                ================================================= */}

            <div
              className="messages"
              ref={scrollRef}
            >

              {messages.map((message) => (

                <div
                  key={message.id}
                  className={`row ${message.role}`}
                >

                  <div
                    className={`bubble ${message.role}`}
                  >

                    {/* =================================================
                        IMPORTANT:
                        ReactMarkdown + remarkMath + rehypeKatex

                        This renders:

                        **bold**

                        - bullets

                        $x^2$

                        $$

                        \frac{96 \times 25}{100}

                        $$

                        properly.
                        ================================================= */}

                    <ReactMarkdown
                      remarkPlugins={[
                        remarkGfm,
                        remarkMath,
                      ]}
                      rehypePlugins={[
                        rehypeKatex,
                      ]}
                    >
                      {message.text}
                    </ReactMarkdown>

                    {/* Timestamp */}

                    <div className="timestamp">

                      {new Date(
                        message.timestamp
                      ).toLocaleTimeString(
                        [],
                        {
                          hour: "2-digit",
                          minute: "2-digit",
                        }
                      )}

                    </div>

                  </div>

                </div>

              ))}

              {/* =================================================
                  THINKING
                  ================================================= */}

              {thinking && (
                <div className="row assistant">

                  <div className="bubble assistant">

                    <TypingDots />

                  </div>

                </div>
              )}

            </div>

            {/* =================================================
                COMPOSER
                ================================================= */}

            <div className="composer">

              <input
                value={draft}
                onChange={(event) =>
                  setDraft(
                    event.target.value
                  )
                }
                onKeyDown={(event) => {

                  if (
                    event.key === "Enter"
                  ) {

                    event.preventDefault();

                    send();

                  }

                }}
                placeholder="Ask anything…"
              />

              {/* Voice */}

              <button
                className="composer-icon"
                onClick={() =>
                  setMode("voice")
                }
                aria-label="Switch to voice input"
              >
                <Mic size={17} />
              </button>

              {/* Send */}

              <button
                className="send-btn"
                onClick={() => send()}
                disabled={
                  !draft.trim() ||
                  thinking
                }
                aria-label="Send message"
              >
                <Send size={15} />
              </button>

            </div>

          </div>
        )}

      </div>
    </div>
  );
}