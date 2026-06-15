export type Role =
  | "owner"
  | "admin"
  | "compliance"
  | "analyst"
  | "sales_bd"
  | "reviewer"
  | "viewer";

export interface AuthSession {
  user_id: string;
  email: string;
  display_name: string;
  organization_id: string;
  role: Role;
  session_id: string;
  expires_at: string;
}

export interface LoginRequest {
  email: string;
  password: string;
  organization_id?: string;
}

export interface LoginResponse {
  session: AuthSession;
  expires_in: number;
}

export interface AuthBootstrapStatus {
  has_users: boolean;
  default_organization_id: string;
  default_email: string;
}

export interface AuthBootstrap {
  authenticated: boolean;
  session?: AuthSession;
}
