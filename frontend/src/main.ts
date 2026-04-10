import { createPinia } from "pinia";
import { createApp } from "vue";

import App from "./App.vue";
import { setAccessTokenResolver } from "./api/httpClient";
import { bootstrapAuthSession } from "./bootstrap/authBootstrap";
import { router } from "./router";
import { useAuthStore } from "./stores/auth";
import "bootstrap/dist/css/bootstrap.min.css";
import "./styles.css";

const app = createApp(App);
const pinia = createPinia();

app.use(pinia);

const authStore = useAuthStore(pinia);
setAccessTokenResolver(() => authStore.accessToken);

async function bootstrapApplication(): Promise<void> {
  await bootstrapAuthSession(authStore);
  app.use(router);
  app.mount("#app");
}

void bootstrapApplication();
