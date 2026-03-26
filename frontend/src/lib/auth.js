export function buildLoginRedirect(path = '/') {
	return `/login?redirect-to=${encodeURIComponent(`/wiki${path}`)}`;
}

export function redirectToLogin(path = window.location.pathname.replace(/^\/wiki/, '') || '/') {
	window.location.href = buildLoginRedirect(path);
}
