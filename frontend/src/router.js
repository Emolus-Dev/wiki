import { createRouter, createWebHistory } from "vue-router";

import { redirectToLogin } from "@/lib/auth";

const routes = [
  {
    path: "/",
    name: "Home",
    redirect: "/spaces",
  },
  {
    path: "/spaces",
    name: "SpaceList",
    component: () => import("@/pages/Spaces.vue"),
  },
  {
    path: "/change-requests",
    name: "ChangeRequests",
    component: () => import("@/pages/Contributions.vue"),
  },
  {
    path: "/change-requests/:changeRequestId",
    name: "ChangeRequestReview",
    component: () => import("@/pages/ContributionReview.vue"),
    props: true,
  },
  {
    path: "/contributions",
    redirect: { name: "ChangeRequests" },
  },
  {
    path: "/contributions/:batchId",
    redirect: (to) => ({
      name: "ChangeRequestReview",
      params: { changeRequestId: to.params.batchId },
    }),
  },
  {
    path: "/spaces/:spaceId",
    component: () => import("@/pages/SpaceDetails.vue"),
    props: true,
    children: [
      {
        path: "",
        name: "SpaceDetails",
        component: () => import("@/components/SpaceWelcome.vue"),
      },
      {
        path: "page/:pageId",
        name: "SpacePage",
        component: () => import("@/components/WikiDocumentPanel.vue"),
        props: true,
      },
      {
        path: "draft/:docKey",
        name: "DraftChangeRequest",
        component: () => import("@/components/DraftContributionPanel.vue"),
        props: true,
      },
      {
        path: "draft/:contributionId",
        redirect: (to) => ({
          name: "DraftChangeRequest",
          params: {
            spaceId: to.params.spaceId,
            docKey: to.params.contributionId,
          },
        }),
      },
    ],
  },
];

const router = createRouter({
  history: createWebHistory("/wiki"),
  routes,
});

async function ensureAuthenticated() {
  const { useSessionStore } = await import("@/stores/session");
  const { useUserStore } = await import("@/stores/user");
  const sessionStore = useSessionStore();
  const userStore = useUserStore();
  sessionStore.refreshFromCookies();

  if (!sessionStore.isLoggedIn) {
    return false;
  }

  try {
    await userStore.bootstrap();
    return true;
  } catch (error) {
    return false;
  }
}

router.beforeEach(async (to, from, next) => {
  const isAuthenticated = await ensureAuthenticated();

  if (!isAuthenticated) {
    redirectToLogin(to.fullPath);
    return;
  }

  next();
});

export default router;
