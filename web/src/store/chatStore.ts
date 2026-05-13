import { create } from "zustand";
import type { Assistant, ChatEvent, ContactListItem } from "@/types/chat";

type ChatState = {
  contacts: ContactListItem[];
  selectedId: string | null;
  eventsByContact: Record<string, ChatEvent[]>;
  candidatesByContact: Record<string, string[]>;
  assistants: Assistant[];
  selectedAssistantByContact: Record<string, string | null>;

  setContacts: (items: ContactListItem[]) => void;
  select: (contactId: string) => void;
  setEvents: (contactId: string, items: ChatEvent[]) => void;
  setCandidates: (contactId: string, items: string[]) => void;
  setAssistants: (items: Assistant[]) => void;
  setSelectedAssistant: (contactId: string, roleId: string | null) => void;
};

export const useChatStore = create<ChatState>((set, get) => ({
  contacts: [],
  selectedId: null,
  eventsByContact: {},
  candidatesByContact: {},
  assistants: [],
  selectedAssistantByContact: {},

  setContacts: (items) => set({ contacts: items }),
  select: (contactId) => {
    const cur = get().selectedId;
    if (cur === contactId) return;
    set({ selectedId: contactId });
  },
  setEvents: (contactId, items) =>
    set((s) => ({
      eventsByContact: {
        ...s.eventsByContact,
        [contactId]: items,
      },
    })),
  setCandidates: (contactId, items) =>
    set((s) => ({
      candidatesByContact: {
        ...s.candidatesByContact,
        [contactId]: items,
      },
    })),

  setAssistants: (items) => set({ assistants: items }),
  setSelectedAssistant: (contactId, roleId) =>
    set((s) => ({
      selectedAssistantByContact: {
        ...s.selectedAssistantByContact,
        [contactId]: roleId,
      },
    })),
}));
