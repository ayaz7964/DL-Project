import React, { useState, useLayoutEffect, useRef, useEffect } from "react";
import { askBackend } from "./api";

// Helper: render text with line breaks + link detection
function renderTextWithBreaks(text) {
  const lines = text.split("\n").map((line, index) => {
    const urlRegex = /(https?:\/\/[^\s]+)/g;
    const parts = line.split(urlRegex);
    return (
      <React.Fragment key={index}>
        {parts.map((part, partIndex) => {
          if (part.match(urlRegex)) {
            return (
              <a
                key={partIndex}
                href={part}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-200 hover:text-white underline"
              >
                {part}
              </a>
            );
          }
          return part;
        })}
        {index < text.split("\n").length - 1 && <br />}
      </React.Fragment>
    );
  });
  return lines;
}

const TypingIndicator = () => (
  <div className="flex items-center gap-3 px-4 py-3 bg-white/10 text-white rounded-2xl max-w-md shadow-lg">
    <div className="w-9 h-9 rounded-full bg-gradient-to-br from-fuchsia-500 to-indigo-500 flex items-center justify-center">
      <span className="text-sm font-semibold">S</span>
    </div>
    <div className="flex items-center gap-2">
      <span className="w-2.5 h-2.5 rounded-full bg-white/70 animate-pulse" />
      <span className="w-2.5 h-2.5 rounded-full bg-white/50 animate-pulse" style={{ animationDelay: "0.15s" }} />
      <span className="w-2.5 h-2.5 rounded-full bg-white/30 animate-pulse" style={{ animationDelay: "0.3s" }} />
    </div>
    <span className="text-sm text-white/80">SIBA Assistant is typing</span>
  </div>
);

const ChatMessage = ({ m }) => {
  const isUser = m.role === "user";
  return (
    <div className={`flex items-end ${isUser ? "justify-end" : "justify-start"} gap-3`}>
      {!isUser && (
        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-fuchsia-500 to-indigo-500 text-white flex items-center justify-center font-semibold shadow-lg">
          S
        </div>
      )}
      <div className={`max-w-[78%] flex flex-col ${isUser ? "items-end" : "items-start"}`}>
        <div
          className={`px-4 py-3 rounded-2xl shadow-lg border border-white/5 ${
            isUser
              ? "bg-gradient-to-r from-fuchsia-500 to-indigo-500 text-white rounded-br-md"
              : "bg-white/10 text-white rounded-bl-md"
          }`}
          style={{ wordBreak: "break-word", lineHeight: 1.6 }}
        >
          {isUser ? m.text : renderTextWithBreaks(m.text)}
        </div>
        <span className="text-xs text-white/50 mt-1">{m.time}</span>
      </div>
      {isUser && (
        <div className="w-10 h-10 rounded-full bg-sky-500 text-white flex items-center justify-center font-semibold shadow-lg">
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" d="M12 12c2.5 0 4.5-2 4.5-4.5S14.5 3 12 3 7.5 5 7.5 7.5 9.5 12 12 12Zm0 0c-3 0-6 1.5-6 4.5V19c0 .6.4 1 1 1h10c.6 0 1-.4 1-1v-2.5c0-3-3-4.5-6-4.5Z" />
          </svg>
        </div>
      )}
    </div>
  );
};

export default function App() {
  const defaultWelcome = {
    id: 1,
    role: "assistant",
    text: "Welcome to **Sukkur IBA University**!\nI'm your dedicated Student Assistant, ready to help you with **admissions, fees, programs, and scholarships**.",
    time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
  };

  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const feedRef = useRef(null);
  const bottomRef = useRef(null);
  const taRef = useRef(null);

  // Load messages from localStorage on mount
  useEffect(() => {
    const stored = localStorage.getItem("siba_chat_history");
    if (stored) {
      try {
        const parsed = JSON.parse(stored);
        if (Array.isArray(parsed) && parsed.length > 0) {
          setMessages(parsed);
          return;
        }
      } catch {
        /* ignore parse errors */
      }
    }
    setMessages([defaultWelcome]);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Persist messages to localStorage
  useEffect(() => {
    if (messages && messages.length) {
      localStorage.setItem("siba_chat_history", JSON.stringify(messages.slice(-50)));
    }
  }, [messages]);

  useLayoutEffect(() => {
    if (bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: "smooth" });
    } else if (feedRef.current) {
      feedRef.current.scrollTo({ top: feedRef.current.scrollHeight, behavior: "smooth" });
    }
  }, [messages, isTyping]);

  const handleInputChange = (e) => {
    setInput(e.target.value);
    if (taRef.current) {
      taRef.current.style.height = "auto";
      taRef.current.style.height = Math.min(taRef.current.scrollHeight, 120) + "px";
    }
  };

  const send = async () => {
    const text = input.trim();
    if (!text || isTyping) return;

    const now = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    const userMsg = { id: Date.now(), role: "user", text, time: now };
    setMessages((m) => [...m, userMsg]);
    setInput("");
    if (taRef.current) taRef.current.style.height = "auto";
    setIsTyping(true);

    const historyPayload = [...messages, userMsg]
      .slice(-20)
      .map((m) => ({ role: m.role, text: m.text }));

    try {
      const reply = await askBackend(text, historyPayload);
      const botMsg = { id: Date.now() + 1, role: "assistant", text: reply, time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) };
      setMessages((m) => [...m, botMsg]);
    } catch {
      const botMsg = { id: Date.now() + 1, role: "assistant", text: "Sorry, something went wrong. Please try again.", time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) };
      setMessages((m) => [...m, botMsg]);
    } finally {
      setIsTyping(false);
    }
  };

  const handleKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  return (
    <div
      className="min-h-screen flex flex-col text-white"
      style={{
        background: "radial-gradient(circle at 20% 20%, rgba(117, 63, 255, 0.2), transparent 35%), radial-gradient(circle at 80% 0%, rgba(0, 195, 255, 0.15), transparent 30%), linear-gradient(135deg, #0f1429 0%, #13193a 50%, #0c102d 100%)",
      }}
    >
      {/* Header */}
      <header className="px-4 md:px-10 py-5 border-b border-white/5 bg-white/5 backdrop-blur-xl shadow-lg">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="w-11 h-11 sm:w-12 sm:h-12 rounded-full bg-gradient-to-br from-fuchsia-500 to-indigo-500 flex items-center justify-center font-bold text-white text-lg shadow-lg">
              S
            </div>
            <div>
              <h1 className="text-lg sm:text-xl font-bold text-white">SIBA Student Assistant</h1>
              <p className="text-sm text-white/70">Powered by Advanced AI</p>
            </div>
          </div>
          <div className="flex items-center gap-2 text-xs sm:text-sm font-semibold text-white">
            <span className="w-3 h-3 rounded-full bg-emerald-400 animate-pulse" />
            Online & Ready
          </div>
        </div>
      </header>

      {/* Chat feed */}
      <main ref={feedRef} className="flex-1 overflow-y-auto px-3 md:px-8 py-6">
        <div className="max-w-4xl mx-auto w-full space-y-6">
          {messages.map((m) => (
            <ChatMessage key={m.id} m={m} />
          ))}
          {isTyping && <TypingIndicator />}
          <div ref={bottomRef} />
        </div>
      </main>

      {/* Input bar */}
      <footer className="sticky bottom-0 px-3 md:px-8 py-5 bg-gradient-to-r from-[#1b1f3b] to-[#0f1434] border-t border-white/5 shadow-2xl z-20">
        <div className="max-w-4xl mx-auto w-full">
          <div className="flex flex-col sm:flex-row items-stretch sm:items-end gap-3 bg-white/5 border border-white/10 rounded-2xl p-3 shadow-xl backdrop-blur focus-within:ring-2 focus-within:ring-fuchsia-400">
            <textarea
              ref={taRef}
              rows={1}
              placeholder="Ask about admissions, fees, programs, or scholarships..."
              value={input}
              onChange={handleInputChange}
              onKeyDown={handleKey}
              disabled={isTyping}
              className="flex-1 bg-transparent resize-none text-white placeholder-white/50 focus:outline-none text-base leading-relaxed"
              style={{ maxHeight: 120 }}
            />
            <div className="flex justify-end">
              <button
                onClick={send}
                disabled={!input.trim() || isTyping}
                className="w-12 h-12 rounded-full bg-gradient-to-br from-fuchsia-500 to-indigo-500 flex items-center justify-center shadow-lg hover:scale-105 active:scale-95 transition disabled:opacity-50"
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6 text-white" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M2.94 2.94a1.5 1.5 0 0 1 1.57-.35l12.5 4.69a1.5 1.5 0 0 1 0 2.84l-12.5 4.69A1.5 1.5 0 0 1 2 13.5v-2.76l6.94-1.42a.5.5 0 1 0-.2-.98L2 7.92V5.5a1.5 1.5 0 0 1 .94-1.38Z" />
                </svg>
              </button>
            </div>
          </div>
          <div className="text-xs text-white/60 mt-2 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1">
            <span>Press <b>Enter</b> to send &nbsp;|&nbsp; <b>Shift+Enter</b> for new line</span>
            <span className="text-right">Powered by Sukkur IBA</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
