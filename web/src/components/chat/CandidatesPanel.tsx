import { Check, Copy, RefreshCcw } from "lucide-react";
import { Plus, Sparkles } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import clsx from "clsx";

import type { Assistant } from "@/types/chat";

type Props = {
  contactId: string | null;
  candidates: string[];
  assistants: Assistant[];
  selectedAssistantId: string | null;
  onSelectAssistant: (roleId: string) => void;
  onCreateAssistant: (input: { name: string; system_prompt: string }) => void;
  onGenerate: () => void;
  onRefresh: () => void;
  errorText: string | null;
};

export function CandidatesPanel({
  contactId,
  candidates,
  assistants,
  selectedAssistantId,
  onSelectAssistant,
  onCreateAssistant,
  onGenerate,
  onRefresh,
  errorText,
}: Props) {
  const [copiedIdx, setCopiedIdx] = useState<number | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [draft, setDraft] = useState({ name: "", system_prompt: "" });
  const items = useMemo(() => candidates.slice(0, 5), [candidates]);

  useEffect(() => {
    setCopiedIdx(null);
  }, [contactId]);

  useEffect(() => {
    if (!contactId) return;
    if (selectedAssistantId) return;
    if (assistants[0]?.role_id) {
      onSelectAssistant(assistants[0].role_id);
    }
  }, [assistants, contactId, onSelectAssistant, selectedAssistantId]);

  async function copyText(text: string, idx: number) {
    await navigator.clipboard.writeText(text);
    setCopiedIdx(idx);
    window.setTimeout(() => setCopiedIdx((v) => (v === idx ? null : v)), 1200);
  }

  return (
    <div className="relative flex h-full min-h-0 flex-col border-l border-zinc-200 bg-white">
      <div className="flex items-center justify-between border-b border-zinc-200 px-4 py-3">
        <div>
          <div className="text-sm font-semibold text-zinc-900">建议回复</div>
          <div className="text-xs text-zinc-500">3–5 条</div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowCreate(true)}
            className={clsx(
              "inline-flex items-center gap-2 rounded-xl border border-zinc-200 px-3 py-2 text-xs text-zinc-700 transition",
              "hover:bg-zinc-50"
            )}
          >
            <Plus className="h-4 w-4" />
            新助手
          </button>
          <button
            onClick={onRefresh}
            className={clsx(
              "inline-flex items-center gap-2 rounded-xl border border-zinc-200 px-3 py-2 text-xs text-zinc-700 transition",
              "hover:bg-zinc-50"
            )}
          >
            <RefreshCcw className="h-4 w-4" />
            刷新
          </button>
        </div>
      </div>

      <div className="border-b border-zinc-200 px-4 py-3">
        <div className="mb-2 text-xs font-medium text-zinc-700">选择助手</div>
        <div className="flex items-center gap-2">
          <select
            disabled={!contactId}
            value={selectedAssistantId || ""}
            onChange={(e) => onSelectAssistant(e.target.value)}
            className="w-full rounded-xl border border-zinc-200 bg-white px-3 py-2 text-sm text-zinc-900"
          >
            <option value="" disabled>
              {contactId ? "请选择" : "先选择联系人"}
            </option>
            {assistants.map((a) => (
              <option key={a.role_id} value={a.role_id}>
                {a.name}
              </option>
            ))}
          </select>
          <button
            disabled={!contactId}
            onClick={onGenerate}
            className={clsx(
              "inline-flex shrink-0 items-center gap-2 rounded-xl bg-zinc-900 px-3 py-2 text-xs font-medium text-white transition",
              contactId ? "hover:bg-zinc-800" : "opacity-50"
            )}
          >
            <Sparkles className="h-4 w-4" />
            生成
          </button>
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-auto p-4">
        {errorText ? (
          <div className="rounded-2xl border border-rose-200 bg-rose-50 p-3 text-xs text-rose-700">{errorText}</div>
        ) : null}
        {!contactId ? (
          <div className="rounded-2xl border border-zinc-200 bg-zinc-50 p-4 text-sm text-zinc-600">先从左侧选择联系人</div>
        ) : items.length === 0 ? (
          <div className="rounded-2xl border border-zinc-200 bg-zinc-50 p-4 text-sm text-zinc-600">
            暂无建议回复。收到新消息后会自动生成。
          </div>
        ) : (
          <div className="space-y-3">
            {items.map((t, idx) => (
              <div key={`${idx}-${t.slice(0, 24)}`} className="rounded-2xl border border-zinc-200 bg-white p-3">
                <div className="whitespace-pre-wrap break-words text-sm leading-relaxed text-zinc-900">{t}</div>
                <div className="mt-3 flex justify-end">
                  <button
                    onClick={() => copyText(t, idx)}
                    className={clsx(
                      "inline-flex items-center gap-2 rounded-xl bg-emerald-600 px-3 py-2 text-xs font-medium text-white transition",
                      "hover:bg-emerald-700"
                    )}
                  >
                    {copiedIdx === idx ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                    {copiedIdx === idx ? "已复制" : "一键复制"}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {showCreate ? (
        <div className="absolute inset-0 z-10 flex items-center justify-center bg-black/30 p-6">
          <div className="w-full max-w-md rounded-2xl bg-white p-4 shadow-xl">
            <div className="mb-3 text-sm font-semibold text-zinc-900">创建新助手</div>
            <div className="space-y-3">
              <Field
                label="名称"
                value={draft.name}
                onChange={(v) => setDraft((d) => ({ ...d, name: v }))}
                placeholder="比如：温柔朋友"
              />
              <TextArea
                label="系统提示词"
                value={draft.system_prompt}
                onChange={(v) => setDraft((d) => ({ ...d, system_prompt: v }))}
                placeholder="比如：你是我在微信里的私人助理，回复要简短、口语化，尽量像我本人。"
              />
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <button
                onClick={() => setShowCreate(false)}
                className="rounded-xl border border-zinc-200 px-3 py-2 text-xs text-zinc-700 hover:bg-zinc-50"
              >
                取消
              </button>
              <button
                onClick={() => {
                  onCreateAssistant(draft);
                  setShowCreate(false);
                  setDraft({ name: "", system_prompt: "" });
                }}
                className="rounded-xl bg-emerald-600 px-3 py-2 text-xs font-medium text-white hover:bg-emerald-700"
              >
                创建
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
}) {
  return (
    <label className="block">
      <div className="mb-1 text-xs font-medium text-zinc-700">{label}</div>
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full rounded-xl border border-zinc-200 px-3 py-2 text-sm text-zinc-900"
      />
    </label>
  );
}

function TextArea({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
}) {
  return (
    <label className="block">
      <div className="mb-1 text-xs font-medium text-zinc-700">{label}</div>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        rows={5}
        className="w-full resize-none rounded-xl border border-zinc-200 px-3 py-2 text-sm text-zinc-900"
      />
    </label>
  );
}
