import clsx from "clsx";
import { useEffect, useMemo, useRef, useState } from "react";

import type { ChatEvent } from "@/types/chat";

type Props = {
  contactId: string | null;
  contactTitle: string;
  events: ChatEvent[];
};

export function ChatPanel({ contactId, contactTitle, events }: Props) {
  const scrollerRef = useRef<HTMLDivElement | null>(null);
  const [stickToBottom, setStickToBottom] = useState(true);

  const messages = useMemo(() => {
    return events
      .filter((e) => e.direction !== "candidate")
      .sort((a, b) => (a.timestamp || 0) - (b.timestamp || 0));
  }, [events]);

  useEffect(() => {
    const el = scrollerRef.current;
    if (!el) return;
    if (!stickToBottom) return;
    el.scrollTop = el.scrollHeight;
  }, [messages, stickToBottom]);

  useEffect(() => {
    setStickToBottom(true);
    const el = scrollerRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [contactId]);

  return (
    <div className="flex h-full min-h-0 flex-col bg-zinc-50">
      <div className="flex items-center justify-between border-b border-zinc-200 bg-white px-4 py-3">
        <div className="min-w-0">
          <div className="truncate text-sm font-semibold text-zinc-900">{contactId ? contactTitle : "请选择联系人"}</div>
          {contactId ? <div className="truncate text-xs text-zinc-500">{contactId}</div> : null}
        </div>
        <div className="text-xs text-zinc-400">实时刷新（轮询）</div>
      </div>

      <div
        ref={scrollerRef}
        className="min-h-0 flex-1 overflow-auto px-4 py-4"
        onScroll={(e) => {
          const el = e.currentTarget;
          const nearBottom = el.scrollHeight - (el.scrollTop + el.clientHeight) < 80;
          setStickToBottom(nearBottom);
        }}
      >
        {!contactId ? (
          <div className="mx-auto mt-20 max-w-md rounded-2xl border border-zinc-200 bg-white p-6 text-sm text-zinc-600">
            左侧选择一个联系人后，这里会显示与微信一致的聊天气泡视图。
          </div>
        ) : messages.length === 0 ? (
          <div className="mx-auto mt-20 max-w-md rounded-2xl border border-zinc-200 bg-white p-6 text-sm text-zinc-600">
            暂无消息。等待 WeFlow 推送或导入历史后再查看。
          </div>
        ) : (
          <div className="space-y-3">
            {messages.map((m, idx) => {
              const prev = idx > 0 ? messages[idx - 1] : null;
              const showTime = !prev || Math.abs((m.timestamp || 0) - (prev.timestamp || 0)) >= 300;
              return (
                <div key={m.event_id}>
                  {showTime ? (
                    <div className="my-4 flex items-center justify-center">
                      <div className="rounded-full bg-zinc-200 px-3 py-1 text-xs text-zinc-600">{formatFullTime(m.timestamp)}</div>
                    </div>
                  ) : null}

                  <ChatBubble event={m} />
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

function ChatBubble({ event }: { event: ChatEvent }) {
  const isSelf = event.direction === "outbound";
  const isRevoke = event.direction === "revoke";
  if (isRevoke) {
    return (
      <div className="flex items-center justify-center">
        <div className="rounded-full bg-zinc-200 px-3 py-1 text-xs text-zinc-600">消息被撤回</div>
      </div>
    );
  }

  return (
    <div className={clsx("flex items-end gap-2", isSelf ? "justify-end" : "justify-start")}>
      {!isSelf ? (
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white text-xs font-semibold text-zinc-500 shadow-sm">
          {(event.sender_name || "?").slice(0, 1)}
        </div>
      ) : null}

      <div className={clsx("max-w-[78%] rounded-2xl px-3 py-2 text-sm leading-relaxed shadow-sm", isSelf ? "bg-emerald-500 text-white" : "bg-white text-zinc-900")}>
        <div className="whitespace-pre-wrap break-words">{event.content}</div>
      </div>

      {isSelf ? (
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-emerald-100 text-xs font-semibold text-emerald-700">
          我
        </div>
      ) : null}
    </div>
  );
}

function formatFullTime(ts: number) {
  if (!ts) return "";
  const d = new Date(ts * 1000);
  return d.toLocaleString([], { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" });
}
