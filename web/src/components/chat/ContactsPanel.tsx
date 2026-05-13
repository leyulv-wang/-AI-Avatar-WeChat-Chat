import { Search } from "lucide-react";
import { useMemo, useState } from "react";
import clsx from "clsx";

import type { ContactListItem } from "@/types/chat";

type Props = {
  contacts: ContactListItem[];
  selectedId: string | null;
  onSelect: (contactId: string) => void;
};

export function ContactsPanel({ contacts, selectedId, onSelect }: Props) {
  const [q, setQ] = useState("");
  const filtered = useMemo(() => {
    const qs = q.trim().toLowerCase();
    if (!qs) return contacts;
    return contacts.filter((c) => {
      return (
        c.id.toLowerCase().includes(qs) ||
        c.display_name.toLowerCase().includes(qs) ||
        c.last_preview.toLowerCase().includes(qs)
      );
    });
  }, [contacts, q]);

  return (
    <div className="flex h-full min-h-0 flex-col border-r border-zinc-200 bg-white">
      <div className="p-3">
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400" />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            className="h-10 w-full rounded-xl border border-zinc-200 bg-white pl-9 pr-3 text-sm outline-none focus:ring-2 focus:ring-emerald-200"
            placeholder="搜索联系人 / 会话"
          />
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-auto">
        {filtered.length === 0 ? (
          <div className="px-4 py-6 text-sm text-zinc-500">暂无会话</div>
        ) : (
          <div className="px-2 pb-3">
            {filtered.map((c) => (
              <button
                key={c.id}
                onClick={() => onSelect(c.id)}
                className={clsx(
                  "flex w-full gap-3 rounded-xl px-3 py-3 text-left transition",
                  c.id === selectedId ? "bg-emerald-50" : "hover:bg-zinc-50"
                )}
              >
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-zinc-100 text-sm font-semibold text-zinc-600">
                  {(c.display_name || c.id).slice(0, 1)}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between gap-2">
                    <div className="truncate text-sm font-medium text-zinc-900">{c.display_name || c.id}</div>
                    <div className="shrink-0 text-xs text-zinc-400">{formatTime(c.last_timestamp)}</div>
                  </div>
                  <div className="mt-1 truncate text-xs text-zinc-500">{c.last_preview || ""}</div>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function formatTime(ts: number) {
  if (!ts) return "";
  const d = new Date(ts * 1000);
  const now = new Date();
  const sameDay =
    d.getFullYear() === now.getFullYear() && d.getMonth() === now.getMonth() && d.getDate() === now.getDate();
  if (sameDay) return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  return d.toLocaleDateString([], { month: "2-digit", day: "2-digit" });
}
