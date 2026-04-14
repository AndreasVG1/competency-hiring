export type UserRole = "job_seeker" | "recruiter";

export interface AuthenticatedUser {
  id: number;
  email: string;
  role: UserRole;
  created_at: string;
}

export interface AuthTokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
  user: AuthenticatedUser;
}

export interface RegisterRequest {
  email: string;
  password: string;
  role: UserRole;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RefreshTokenRequest {
  refresh_token: string;
}

export interface ChangePasswordRequest {
  old_password: string;
  new_password: string;
  confirm_new_password: string;
}

export interface DeleteAccountRequest {
  current_password: string;
}
