import "vue-router";

import type { UserRole } from "../types/auth";

declare module "vue-router" {
  interface RouteMeta {
    requiresAuth?: boolean;
    allowedRoles?: UserRole[];
  }
}

