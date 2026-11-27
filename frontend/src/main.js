import { createApp, watchEffect } from 'vue';

import App from './App.vue';
import { watchLongTasks } from './lib/freezeTrace';
import { schedulePruneFinishedDrafts } from './lib/pruneDrafts';
import router from './router';
import { initSocket } from './socket';
import { pinia } from './stores';
import { useSessionStore } from './stores/session';
import { useUserStore } from './stores/user';

import translationPlugin from './translation';

import {
	Badge,
	Button,
	Dialog,
	ErrorMessage,
	FormControl,
	TextInput,
	frappeRequest,
	resourcesPlugin,
	setConfig,
} from 'frappe-ui';

import './index.css';
import './wiki-editor-content.css';

const globalComponents = {
	Button,
	TextInput,
	FormControl,
	ErrorMessage,
	Dialog,
	Badge,
};

watchLongTasks();

const app = createApp(App);

setConfig('resourceFetcher', frappeRequest);

app.use(pinia);

const userStore = useUserStore();
if (!userStore.data) userStore.fetch().catch(() => {});

app.use(router);
app.use(translationPlugin);
app.use(resourcesPlugin);

const session = useSessionStore();
let draftPruneScheduled = false;
watchEffect(() => {
	if (!session.isLoggedIn || draftPruneScheduled) return;
	draftPruneScheduled = true;
	schedulePruneFinishedDrafts();
});

const socket = initSocket();
app.config.globalProperties.$socket = socket;

for (const key in globalComponents) {
	app.component(key, globalComponents[key]);
}

app.mount('#app');
