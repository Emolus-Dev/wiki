import router from '@/router';
import { createResource } from 'frappe-ui';
import { defineStore } from 'pinia';
import { computed } from 'vue';

export const useUserStore = defineStore('user', () => {
	const userResource = createResource({
		url: 'wiki.api.get_user_info',
		cache: 'User',
		onError(error) {
			if (error && error.exc_type === 'AuthenticationError') {
				router.push({ name: 'LoginPage' });
			}
		},
	});

	const isWikiManager = computed(() => {
		const user = userResource.data;
		if (!user || !user.roles) return false;

		return user.roles.some(
			(role) => role.role === 'Wiki Manager' || role.role === 'System Manager',
		);
	});

	return {
		userResource,
		isWikiManager,
	};
});
