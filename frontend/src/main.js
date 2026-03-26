import { createApp } from "vue";

import App from "./App.vue";
import router from "./router";
import { pinia } from "./stores";

import translationPlugin from "./translation";

import {
  Alert,
  Badge,
  Button,
  Dialog,
  ErrorMessage,
  FormControl,
  Input,
  TextInput,
  frappeRequest,
  pageMetaPlugin,
  resourcesPlugin,
  setConfig,
} from "frappe-ui";

import "./index.css";

const globalComponents = {
  Button,
  TextInput,
  Input,
  FormControl,
  ErrorMessage,
  Dialog,
  Alert,
  Badge,
};

const app = createApp(App);

setConfig("resourceFetcher", frappeRequest);

app.use(pinia);
app.use(router);
app.use(translationPlugin);
app.use(resourcesPlugin);
app.use(pageMetaPlugin);

app.config.globalProperties.$socket = null;

for (const key in globalComponents) {
  app.component(key, globalComponents[key]);
}

app.mount("#app");
