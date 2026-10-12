import { expect, test } from '../fixtures';
import { APP_BASE } from '../helpers/routes';

/**
 * Home is the landing page: greeting, search, space cards, recently edited
 * pages and per-browser pinned snippets.
 */

const SPACE_NAME = 'Home Spec Space';
const PAGE_TITLE = 'Home Spec Page';

test.describe('Home page', () => {
	test.beforeAll(async ({ wikiSuite }) => {
		await wikiSuite.space({
			space_name: SPACE_NAME,
			pages: [{ title: PAGE_TITLE, content: 'Home fixture content.' }],
		});
	});

	test('greets the user and lists the space and its recently edited page', async ({
		page,
	}) => {
		await page.setViewportSize({ width: 1440, height: 900 });
		await page.goto(APP_BASE);

		await expect(page.getByTestId('home-greeting')).toContainText('Hello');
		await expect(
			page.getByTestId('home-spaces').getByText(SPACE_NAME),
		).toBeVisible();
		await expect(
			page.getByTestId('home-recent').getByText(PAGE_TITLE),
		).toBeVisible();
	});

	test('the search box opens the command palette', async ({ page }) => {
		await page.setViewportSize({ width: 1440, height: 900 });
		await page.goto(APP_BASE);

		await page.getByTestId('home-search').click();
		await expect(page.getByRole('dialog')).toBeVisible();
	});

	test('a pinned snippet can be added and removed', async ({ page }) => {
		await page.setViewportSize({ width: 1440, height: 900 });
		await page.goto(APP_BASE);

		await page.getByTestId('home-snippet-add').click();
		const dialog = page.getByRole('dialog');
		await dialog.getByLabel('Title').fill('Restart bench');
		await dialog.getByLabel('Code').fill('bench restart');
		await dialog.getByRole('button', { name: 'Pin' }).click();

		const snippet = page.getByTestId('home-snippet').first();
		await expect(snippet).toContainText('Restart bench');
		await expect(snippet).toContainText('bench restart');

		// It is per-browser, so it survives a reload.
		await page.reload();
		await expect(page.getByTestId('home-snippet').first()).toContainText(
			'bench restart',
		);

		await page.getByTestId('home-snippet').first().hover();
		await page
			.getByTestId('home-snippet')
			.first()
			.getByRole('button', { name: 'Remove snippet' })
			.click();
		await expect(page.getByTestId('home-snippet')).toHaveCount(0);
	});
});
