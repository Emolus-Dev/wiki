export function getErrorMessage(error, fallback = __('Something went wrong')) {
	if (!error) return fallback;

	const message = error.messages?.[0] || error.message || error.exc || '';
	return String(message).trim() || fallback;
}

export function logError(context, error) {
	console.error(context, error);
}

export function handleError({ error, context, fallback, notify }) {
	logError(context, error);
	const message = getErrorMessage(error, fallback);
	if (notify) {
		notify(message);
	}
	return message;
}
