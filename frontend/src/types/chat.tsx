export interface ChatMessage {
    type: string;
    player_id: string;
    player_name: string;
    player_role?: string;
    message: string;
    timestamp: number;
    is_explaining?: boolean;
  }