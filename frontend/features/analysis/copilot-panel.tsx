"use client";

import React, { useState } from "react";
import { sendCopilotQuery } from "@/lib/api";
import type { CopilotChatResponse, CopilotCitation } from "@/types/api";
import {
  Sparkles,
  Send,
  Layers,
  HelpCircle,
  ShieldCheck,
  AlertCircle,
  CheckCircle2,
  RefreshCw,
  X,
} from "lucide-react";

interface CopilotPanelProps {
  analysisId: string;
  onNavigateTab: (tab: string) => void;
  onClose?: () => void;
}

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  supportLabel?: string;
  citations?: CopilotCitation[];
}

export const CopilotPanel: React.FC<CopilotPanelProps> = ({
  analysisId,
  onNavigateTab,
  onClose,
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "initial-greeting",
      role: "assistant",
      content:
        "I am your XAI-ResOpt Copilot. I inspect your active analysis state, verified evidence graph, and ATS scores to give factually grounded answers. What would you like to explore?",
      supportLabel: "Known from evidence",
      citations: [],
    },
  ]);
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const presetChips = [
    "Why is my score what it is?",
    "Which mandatory skills are missing?",
    "Show evidence for my achievements",
    "Explain proposed rewrites",
  ];

  const handleSendMessage = async (queryText?: string) => {
    const q = (queryText || inputValue).trim();
    if (!q || isLoading) return;

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: q,
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputValue("");
    setIsLoading(true);

    try {
      const resp: CopilotChatResponse = await sendCopilotQuery(analysisId, q);
      const assistantMsg: ChatMessage = {
        id: `assistant-${Date.now()}`,
        role: "assistant",
        content: resp.response,
        supportLabel: resp.support_label,
        citations: resp.citations,
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      const detailMsg =
        err?.message && typeof err.message === "string" && !err.message.includes("[object Object]")
          ? err.message
          : "Unable to query copilot engine. Please verify the backend service is reachable.";
      const errorMsg: ChatMessage = {
        id: `error-${Date.now()}`,
        role: "assistant",
        content: `Error: ${detailMsg}`,
        supportLabel: "Unknown",
        citations: [],
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  const getSupportBadge = (label?: string) => {
    switch (label) {
      case "Known from evidence":
        return (
          <span className="rounded bg-[#f0f7f2] border border-[#cde4d3] px-2 py-0.5 text-[10px] font-semibold text-[#1f6339] flex items-center gap-1 font-mono">
            <CheckCircle2 className="h-3 w-3" /> [Known from evidence]
          </span>
        );
      case "Inferred":
        return (
          <span className="rounded bg-[#fdf8ee] border border-[#fae8be] px-2 py-0.5 text-[10px] font-semibold text-[#8c6218] font-mono">
            [Inferred]
          </span>
        );
      case "Unsupported":
        return (
          <span className="rounded bg-[#fdf2f0] border border-[#f7d0ca] px-2 py-0.5 text-[10px] font-semibold text-[#942e23] font-mono">
            [Unsupported]
          </span>
        );
      default:
        return (
          <span className="rounded bg-[#f7f5ef] border border-[#ded9cc] px-2 py-0.5 text-[10px] font-semibold text-[#5c5953] font-mono">
            [Unknown]
          </span>
        );
    }
  };

  return (
    <aside
      role="region"
      aria-label="Grounded AI Copilot"
      className="flex h-full flex-col rounded border border-[#e6e2d8] bg-[#ffffff] shadow-editorial"
    >
      {/* Header */}
      <div className="flex items-center justify-between border-b border-[#edeae1] p-4">
        <div className="flex items-center gap-2">
          <span className="flex h-6 w-6 items-center justify-center rounded bg-[#181816] text-[10px] font-bold text-[#fcfbf7]">
            AI
          </span>
          <div>
            <h3 className="text-xs font-serif font-normal text-[#181816]">Grounded Copilot</h3>
            <span className="text-[10px] font-mono text-[#5c5953]">Current Analysis Context</span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-[#1f6339]" title="Grounded context active" />
          {onClose && (
            <button
              onClick={onClose}
              className="flex items-center justify-center rounded p-1.5 text-[#5c5953] hover:bg-[#f7f5ef] hover:text-[#181816] min-h-[40px] min-w-[40px] transition-colors"
              aria-label="Close copilot drawer"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>
      </div>

      {/* Preset Query Chips */}
      <div className="border-b border-[#edeae1] bg-[#fcfbf7] p-3">
        <span className="text-[10px] font-mono text-[#5c5953] uppercase font-bold block mb-1.5">
          Suggested Inquiries:
        </span>
        <div className="flex flex-wrap gap-1.5">
          {presetChips.map((chip, idx) => (
            <button
              key={idx}
              onClick={() => handleSendMessage(chip)}
              disabled={isLoading}
              className="rounded border border-[#ded9cc] bg-[#ffffff] px-2.5 py-1.5 text-[11px] text-[#5c5953] hover:border-[#181816] hover:text-[#181816] transition-colors disabled:opacity-50 text-left min-h-[36px] flex items-center"
            >
              {chip}
            </button>
          ))}
        </div>
      </div>

      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 text-xs">
        {messages.map((msg) => {
          const isUser = msg.role === "user";
          return (
            <div
              key={msg.id}
              className={`flex flex-col ${isUser ? "items-end" : "items-start"}`}
            >
              <div
                className={`max-w-[90%] rounded p-3 text-xs leading-relaxed ${
                  isUser
                    ? "bg-[#181816] text-[#fcfbf7]"
                    : "bg-[#fcfbf7] border border-[#edeae1] text-[#181816]"
                }`}
              >
                {!isUser && (
                  <div className="mb-2 flex items-center justify-between border-b border-[#edeae1] pb-1.5">
                    {getSupportBadge(msg.supportLabel)}
                  </div>
                )}
                <p>{msg.content}</p>

                {/* Evidence Citations if available */}
                {msg.citations && msg.citations.length > 0 && (
                  <div className="mt-3 border-t border-[#edeae1] pt-2 space-y-1.5">
                    <span className="font-mono text-[10px] uppercase text-[#5c5953] font-bold block">
                      Evidence Provenance:
                    </span>
                    {msg.citations.map((c, i) => (
                      <button
                        key={i}
                        type="button"
                        onClick={() => {
                          onNavigateTab("evidence");
                          if (onClose) onClose();
                        }}
                        className="w-full text-left rounded border border-[#ded9cc] bg-[#ffffff] p-2 text-[11px] hover:border-[#181816] transition-colors focus-visible:ring-2 focus-visible:ring-[#181816]"
                      >
                        <span className="font-mono text-[10px] text-[#1f6339] font-semibold block">
                          {c.source} ({(c.confidence * 100).toFixed(0)}% confidence)
                        </span>
                        <p className="text-[#5c5953] mt-0.5">&quot;{c.text}&quot;</p>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          );
        })}

        {isLoading && (
          <div className="flex items-center gap-2 text-xs text-[#5c5953] p-2">
            <RefreshCw className="h-3 w-3 animate-spin text-[#181816]" />
            Retrieving grounded analysis context...
          </div>
        )}
      </div>

      {/* Input Box */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleSendMessage();
        }}
        className="border-t border-[#edeae1] p-3 flex items-center gap-2 bg-[#ffffff]"
      >
        <label htmlFor="copilot-input-field" className="sr-only">
          Ask Copilot a question
        </label>
        <input
          id="copilot-input-field"
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          placeholder="Ask why a score was given or request evidence..."
          className="flex-1 rounded border border-[#ded9cc] bg-[#fcfbf7] px-3 py-2 text-xs text-[#181816] focus:border-[#181816] focus:outline-none min-h-[44px]"
        />
        <button
          type="submit"
          disabled={isLoading || !inputValue.trim()}
          className="rounded bg-[#181816] p-2 text-[#fcfbf7] hover:bg-[#2b2926] disabled:opacity-40 transition-colors shadow-sm min-h-[44px] min-w-[44px] flex items-center justify-center"
          aria-label="Send query"
          title="Send query"
        >
          <Send className="h-4 w-4" />
        </button>
      </form>
    </aside>
  );
};
