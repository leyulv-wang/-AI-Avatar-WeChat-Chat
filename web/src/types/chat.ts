export type ContactListItem = {
  id: string;
  display_name: string;
  last_timestamp: number;
  last_preview: string;
};

export type ChatEvent = {
  event_id: string;
  contact_id: string;
  contact_name?: string | null;
  timestamp: number;
  sender: string;
  sender_name?: string | null;
  direction: "inbound" | "outbound" | "candidate" | "revoke";
  content: string;
  platform_message_id?: string | null;
  ai_candidates?: string[] | null;
};

export type Assistant = {
  role_id: string;
  name: string;
  system_prompt: string;
};
