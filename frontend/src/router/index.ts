import { createRouter, createWebHistory, type RouteLocationNormalized } from "vue-router";

import { useAuthStore } from "../stores/auth";
import type { UserRole } from "../types/auth";
import AuthLayoutView from "../views/auth/AuthLayoutView.vue";
import LoginView from "../views/auth/LoginView.vue";
import RegisterView from "../views/auth/RegisterView.vue";
import RecruiterHomeView from "../views/recruiter/RecruiterHomeView.vue";
import RecruiterJobOfferCreateView from "../views/recruiter/RecruiterJobOfferCreateView.vue";
import RecruiterJobOfferDetailView from "../views/recruiter/RecruiterJobOfferDetailView.vue";
import RecruiterJobOfferEditView from "../views/recruiter/RecruiterJobOfferEditView.vue";
import RecruiterLayoutView from "../views/recruiter/RecruiterLayoutView.vue";
import RecruiterProfileEditView from "../views/recruiter/RecruiterProfileEditView.vue";
import SeekerEditView from "../views/seeker/SeekerEditView.vue";
import SeekerHomeView from "../views/seeker/SeekerHomeView.vue";
import SeekerLayoutView from "../views/seeker/SeekerLayoutView.vue";

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
      component: SeekerLayoutView,
      meta: {
        requiresAuth: true,
        allowedRoles: ["job_seeker"],
      },
      children: [
        {
          path: "",
          name: SEEKER_HOME_ROUTE_NAME,
          component: SeekerHomeView,
        },
        {
          path: "edit",
          name: "seeker-edit",
          component: SeekerEditView,
        },
      ],
    },
    {
      path: "/recruiter",
      component: RecruiterLayoutView,
      meta: {
        requiresAuth: true,
        allowedRoles: ["recruiter"],
      },
      children: [
        {
          path: "",
          name: RECRUITER_HOME_ROUTE_NAME,
          component: RecruiterHomeView,
        },
        {
          path: "edit",
          name: "recruiter-edit",
          component: RecruiterProfileEditView,
        },
        {
          path: "job-offers/new",
          name: "recruiter-job-offer-new",
          component: RecruiterJobOfferCreateView,
        },
        {
          path: "job-offers/:id",
          name: "recruiter-job-offer-detail",
          component: RecruiterJobOfferDetailView,
        },
        {
          path: "job-offers/:id/edit",
          name: "recruiter-job-offer-edit",
          component: RecruiterJobOfferEditView,
        },
      ],
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
