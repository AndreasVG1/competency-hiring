import { createRouter, createWebHistory, type RouteLocationNormalized } from "vue-router";

import { useAuthStore } from "../stores/auth";
import type { UserRole } from "../types/auth";
import AuthLayoutView from "../views/auth/AuthLayoutView.vue";
import LoginView from "../views/auth/LoginView.vue";
import RegisterView from "../views/auth/RegisterView.vue";
import RecruiterHomeView from "../views/recruiter/RecruiterHomeView.vue";
import SeekerHomeView from "../views/seeker/SeekerHomeView.vue";

const SEEKER_HOME_ROUTE_NAME = "seeker-home";
const RECRUITER_HOME_ROUTE_NAME = "recruiter-home";
const LOGIN_ROUTE_NAME = "auth-login";

function getHomeRouteByRole(role: UserRole | null): string {
  if (role === "recruiter") {
    return RECRUITER_HOME_ROUTE_NAME;
  }
  return SEEKER_HOME_ROUTE_NAME;
}

function extractAllowedRoles(route: RouteLocationNormalized): UserRole[] | undefined {
  for (let i = route.matched.length - 1; i >= 0; i -= 1) {
    const roles = route.matched[i].meta.allowedRoles;
    if (roles) {
      return roles;
    }
  }
  return undefined;
}

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/",
      redirect: "/auth/login",
    },
    {
      path: "/auth",
      component: AuthLayoutView,
      children: [
        {
          path: "login",
          name: LOGIN_ROUTE_NAME,
          component: LoginView,
          meta: { requiresAuth: false },
        },
        {
          path: "register",
          name: "auth-register",
          component: RegisterView,
          meta: { requiresAuth: false },
        },
      ],
    },
    {
      path: "/seeker",
      name: SEEKER_HOME_ROUTE_NAME,
      component: SeekerHomeView,
      meta: {
        requiresAuth: true,
        allowedRoles: ["job_seeker"],
      },
    },
    {
      path: "/recruiter",
      name: RECRUITER_HOME_ROUTE_NAME,
      component: RecruiterHomeView,
      meta: {
        requiresAuth: true,
        allowedRoles: ["recruiter"],
      },
    },
    {
      path: "/:pathMatch(.*)*",
      redirect: "/auth/login",
    },
  ],
});

router.beforeEach((to) => {
  const authStore = useAuthStore();
  const requiresAuth = to.matched.some((record) => record.meta.requiresAuth);

  if (requiresAuth && !authStore.isAuthenticated) {
    return { name: LOGIN_ROUTE_NAME };
  }

  if (requiresAuth) {
    const allowedRoles = extractAllowedRoles(to);
    if (allowedRoles && authStore.role && !allowedRoles.includes(authStore.role)) {
      return { name: getHomeRouteByRole(authStore.role) };
    }
  }

  if (to.path.startsWith("/auth") && authStore.isAuthenticated) {
    return { name: getHomeRouteByRole(authStore.role) };
  }

  return true;
});

