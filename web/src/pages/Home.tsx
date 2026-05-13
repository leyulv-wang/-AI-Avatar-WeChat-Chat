import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { ChatPanel } from "@/components/chat/ChatPanel";
import { ContactsPanel } from "@/components/chat/ContactsPanel";
import { CandidatesPanel } from "@/components/chat/CandidatesPanel";
import { useInterval } from "@/hooks/useInterval";
import { useChatStore } from "@/store/chatStore";
import {
  createAssistant,
  fetchAssistants,
  fetchCandidates,
  fetchContacts,
  fetchEvents,
  fetchSelectedAssistant,
  generateCandidates,
  setSelectedAssistant,
} from "@/utils/api";

export default function Home() {
  const contacts = useChatStore((s) => s.contacts);
  const selectedId = useChatStore((s) => s.selectedId);
  const eventsByContact = useChatStore((s) => s.eventsByContact);
  const candidatesByContact = useChatStore((s) => s.candidatesByContact);
  const setContacts = useChatStore((s) => s.setContacts);
  const select = useChatStore((s) => s.select);
  const setEvents = useChatStore((s) => s.setEvents);
  const setCandidates = useChatStore((s) => s.setCandidates);
  const assistants = useChatStore((s) => s.assistants);
  const setAssistants = useChatStore((s) => s.setAssistants);
  const selectedAssistantByContact = useChatStore((s) => s.selectedAssistantByContact);
  const setSelectedAssistantLocal = useChatStore((s) => s.setSelectedAssistant);

  const [status, setStatus] = useState<"online" | "reconnecting" | "offline">("reconnecting");
  const [errorText, setErrorText] = useState<string | null>(null);

  const inFlight = useRef({ health: false, contacts: false, selected: false, assistants: false });
  const pageVisibleRef = useRef(true);

  useEffect(() => {
    const onVis = () => {
      pageVisibleRef.current = !document.hidden;
    };
    onVis();
    document.addEventListener("visibilitychange", onVis);
    return () => document.removeEventListener("visibilitychange", onVis);
  }, []);

  const refreshHealth = useCallback(async () => {
    if (!pageVisibleRef.current) return;
    if (inFlight.current.health) return;
    inFlight.current.health = true;
    try {
      const r = await fetch("/health", { method: "GET", cache: "no-store" });
      if (!r.ok) throw new Error(String(r.status));
      setStatus("online");
    } catch {
      setStatus("offline");
    } finally {
      inFlight.current.health = false;
    }
  }, []);

  const selectedContact = useMemo(() => {
    if (!selectedId) return null;
    return contacts.find((c) => c.id === selectedId) || null;
  }, [contacts, selectedId]);

  const selectedEvents = selectedId ? eventsByContact[selectedId] || [] : [];
  const selectedCandidates = selectedId ? candidatesByContact[selectedId] || [] : [];
  const selectedAssistantId = selectedId ? selectedAssistantByContact[selectedId] ?? null : null;

  const refreshAssistants = useCallback(async () => {
    if (!pageVisibleRef.current) return;
    if (inFlight.current.assistants) return;
    inFlight.current.assistants = true;
    try {
      const items = await fetchAssistants();
      setAssistants(items);
    } catch {
      return;
    } finally {
      inFlight.current.assistants = false;
    }
  }, [setAssistants]);

  const handleSelectAssistant = useCallback(
    async (roleId: string) => {
      if (!selectedId) return;
      try {
        await setSelectedAssistant(selectedId, roleId);
        setSelectedAssistantLocal(selectedId, roleId);
        const items = await generateCandidates(selectedId);
        setCandidates(selectedId, items);
        setErrorText(null);
      } catch (e) {
        setErrorText(e instanceof Error ? e.message : "生成失败");
        return;
      }
    },
    [selectedId, setCandidates, setSelectedAssistantLocal]
  );

  const handleGenerate = useCallback(async () => {
    if (!selectedId) return;
    try {
      const items = await generateCandidates(selectedId);
      setCandidates(selectedId, items);
      setErrorText(null);
    } catch (e) {
      setErrorText(e instanceof Error ? e.message : "生成失败");
      return;
    }
  }, [selectedId, setCandidates]);

  const handleCreateAssistant = useCallback(
    async (input: { name: string; system_prompt: string }) => {
      try {
        const created = await createAssistant(input);
        await refreshAssistants();
        if (selectedId) {
          await handleSelectAssistant(created.role_id);
        }
        setErrorText(null);
      } catch (e) {
        setErrorText(e instanceof Error ? e.message : "创建失败");
        return;
      }
    },
    [handleSelectAssistant, refreshAssistants, selectedId]
  );

  const refreshContacts = useCallback(async () => {
    if (!pageVisibleRef.current) return;
    if (inFlight.current.contacts) return;
    inFlight.current.contacts = true;
    try {
      const items = await fetchContacts({ limit: 200 });
      setContacts(items);
      if (!selectedId && items[0]) {
        select(items[0].id);
      }
    } catch {
      return;
    } finally {
      inFlight.current.contacts = false;
    }
  }, [select, selectedId, setContacts]);

  const refreshSelected = useCallback(async () => {
    if (!selectedId) return;
    if (!pageVisibleRef.current) return;
    if (inFlight.current.selected) return;
    inFlight.current.selected = true;
    try {
      const [evts, cands] = await Promise.all([fetchEvents(selectedId, 200), fetchCandidates(selectedId, 5)]);
      setEvents(selectedId, evts);
      setCandidates(selectedId, cands);
    } catch {
      return;
    } finally {
      inFlight.current.selected = false;
    }
  }, [selectedId, setCandidates, setEvents]);

  useEffect(() => {
    void refreshContacts();
  }, [refreshContacts]);

  useEffect(() => {
    void refreshHealth();
  }, [refreshHealth]);

  useEffect(() => {
    void refreshAssistants();
  }, [refreshAssistants]);

  useInterval(() => {
    void refreshAssistants();
  }, 15000);

  useEffect(() => {
    void refreshSelected();
  }, [refreshSelected]);

  useEffect(() => {
    if (!selectedId) return;
    (async () => {
      try {
        const data = await fetchSelectedAssistant(selectedId);
        setSelectedAssistantLocal(selectedId, data.role_id);
      } catch {
        return;
      }
    })();
  }, [selectedId, setSelectedAssistantLocal]);

  useInterval(() => {
    void refreshContacts();
  }, 8000);

  useInterval(() => {
    void refreshHealth();
  }, 5000);

  useInterval(() => {
    void refreshSelected();
  }, selectedId ? 2500 : null);

  const statusLabel = status === "online" ? "在线" : status === "reconnecting" ? "重连中" : "离线";
  const statusDot = status === "online" ? "bg-emerald-500" : status === "reconnecting" ? "bg-amber-400" : "bg-rose-500";

  return (
    <div className="h-screen w-screen overflow-hidden bg-zinc-100">
      <div className="flex h-full min-h-0 flex-col">
        <div className="flex items-center justify-between border-b border-zinc-200 bg-white px-4 py-3">
          <div className="flex items-center gap-3">
            <div className="text-sm font-semibold text-zinc-900">聊天工作台</div>
            <div className="flex items-center gap-2 text-xs text-zinc-600">
              <span className={`h-2 w-2 rounded-full ${statusDot}`} />
              {statusLabel}
            </div>
          </div>
          <div className="text-xs text-zinc-500">个人微信：只做建议回复 + 一键复制</div>
        </div>

        <div className="grid flex-1 min-h-0 grid-cols-[280px_minmax(520px,1fr)_320px] overflow-hidden">
          <ContactsPanel contacts={contacts} selectedId={selectedId} onSelect={select} />
          <ChatPanel
            contactId={selectedId}
            contactTitle={selectedContact?.display_name || selectedId || ""}
            events={selectedEvents}
          />
          <CandidatesPanel
            contactId={selectedId}
            candidates={selectedCandidates}
            assistants={assistants}
            selectedAssistantId={selectedAssistantId}
            onSelectAssistant={handleSelectAssistant}
            onCreateAssistant={handleCreateAssistant}
            onGenerate={handleGenerate}
            onRefresh={refreshSelected}
            errorText={errorText}
          />
        </div>
      </div>
    </div>
  );
}
